# wave-adrgate — rail de MATERIAIS rodada 1 (os 4 scripts, S334)

Rail-Verdict: CHANGES-REQUESTED (1 P1 + 2 P2 — todos REAIS; curados nesta rodada)

Comando: `codex exec` (sandbox read-only) com brief adversarial explícito
(G-gate enfraquecido vs molde F; V-block com direção errada; constante da
F sobrando; kernel-arming; escrita fora do repo / árvore suja no abort).
Saída bruta: `<scratchpad S334>/adrgate-materials-r1.txt`.

## P1 — kernel-arming AUSENTE no LAND (e o codex pegou o meu claim falso)

O LAND armava só `CEO_SENTINEL_UNLOCK`; o patch toca
`.github/workflows/validate.yml` (`_KERNEL_PATHS`) e o sentinel DECLARAVA
"o LAND arma o override" — claim que o script não cumpria. O molde F tem
a MESMA omissão ("mold parity does not satisfy the stated kernel
ceremony" — verbatim do revisor). Cura no molde W3K (o precedente real de
cerimônia de kernel): recusa-se-já-armado na entrada, `export` no MENOR
escopo (imediatamente antes do `git apply`), `unset` explícito pós-commit
e backstop no trap EXIT. O claim do sentinel agora é VERDADEIRO.

## P2-a — restauração não-preservante no abort do LAND

`git reset` global des-stagearia trabalho de terceiros que o G0 tolera;
e a preservação de logs pós-fingerprint deixava a mensagem "restaurados
byte a byte" mentindo, com risco de `cp -p` seguir symlink pré-existente.
Cura: reset SCOPED aos paths derivados do próprio patch; destino de log
pré-existente/symlink RECUSADO; contagem `_logs_kept` com NOTA explícita
de que os logs ficam na árvore DE PROPÓSITO (abort com evidência).

## P2-b — finalize não-transacional

O gerador sobrescreve patch/sentinel/PROPOSED em sequência e um abort dos
checks seguintes deixava os três pela metade; o guard de index rodava
DEPOIS do `git add` e o remédio impresso era `git reset` global. Cura:
backup dos três antes do gerador + restore condicional no trap EXIT
(`_fin_ok` só vira 1 após o commit dos materiais); guard de index
NÃO-VAZIO movido para ANTES do add; mensagens de remédio passam a mandar
reset ESCOPADO.

## Registro sobre o molde F

O P1 e os dois P2 EXISTEM no molde F (`OWNER-S331-F-LAND.sh` /
`finalize-F.sh`), que já landou duas cerimônias reais — ficam como
follow-up de texto para a PRÓXIMA wave que tocar aquela família (a F é
material de cerimônia landada; não se reescreve retroativamente).

## Pós-cura

`bash -n` verde nos 4; harness re-rodado: **19 PASS / 0 FAIL / 0 SKIP**
(T15b agora exercita o arming interno do kernel no land completo).
