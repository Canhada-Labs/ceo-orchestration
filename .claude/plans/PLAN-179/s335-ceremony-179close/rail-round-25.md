# wave-179close — rail codex rodada 25 (sombra pós-curas r24, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (2 P2 — 1 curado, 1 RE-REFUTADO com a mesma evidência; tudo antes da r26)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r25.txt` (13.629
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.
Nenhum achado de RUNTIME — os dois são de material de governança.

## Os achados (verificação + destino)

1. **[P2] Dois blocos "permanece ABERTO" contradiziam o `done`** —
   VERIFICADO REAL (a regra PLAN-SCHEMA §410-411 exige critérios
   fechados no flip): as conclusões do W0 tinham envelhecido em relação
   à própria cerimônia. CURA: os DOIS blocos reconciliados com a
   evidência de fechamento — (a)/US1 #1 SUPERSEDIDOS pela emenda r1-C3
   (registro rail-round-1); custo de gate-boot re-pago MEDIDO na S322
   (97.292 fronteira real / cold-F 97.097, delta 0,20%, instrumento
   `w0/gateboot_repay.py`); válvula do US2b entregue NESTA wave
   (`_eta_advisory`, η=887‰, deny = limite de substrato). `grep ABERTO`
   no plano = 0.
2. **[P2] "FOLLOWUP não existe" (re-levantado)** — RE-REFUTADO com a
   MESMA evidência da r20: `PLAN-179-FOLLOWUP-sessionstart-anchor-id.md`
   está RASTREADO no main desde `af6aaf8` (verificado por
   `git ls-files` no vivo; atualizado em `5ba3d67`/`592d4c6`). O revisor
   lê a sombra cuja base (`cfab980`) precede o commit — o arquivo não
   PODE aparecer lá, e adicioná-lo à sombra abortaria o finalize
   (fora do EXPECTED). No land, o main contém o arquivo e o pointer é
   válido. Classe escopo-do-clone, terceira ocorrência na história das
   cerimônias (W5-r6, r20, r25).

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **350/0** (8.34s) —
contagem inalterada (curas de prosa). Cura confinada a 1 path do
EXPECTED. Refinalize + r26 na sequência.
