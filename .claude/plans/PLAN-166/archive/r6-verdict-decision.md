# PLAN-166 — rail codex round 6: veredito e decisão (S297-noite, 07/08)

Transcript: `codex-r6-2059.md` (este diretório). Rodado sobre a sujeira da
cerimônia (o pack aplicado, não-commitado) na árvore PÓS-PLAN-167.

## Achados e disposição

**r6-P1 — S4 grepa `ADOPTER-FORK` e a WARNING não o carrega.**
CONFIRMADO — e é **convergência independente**: o e2e F3 pegou o mesmo
defeito (44/45) minutos antes, na bateria do land. Causa: REGRESSÃO DO
PLAN-167 (`7c0828a`) — o rewrite do ramo de preservação perdeu o token que o
comentário §1869 do próprio `upgrade.sh` promete ("named WARNING"). NÃO é
defeito do pack do 166 (o teste está certo; o produto regrediu depois).
**Fix já no pack do PLAN-168** (`staged/scripts/upgrade.sh`, provado 45/45
no overlay + INV-4 4/4). O step1b aceita 44/45 SOMENTE com essa única falha
nomeada, e instrui a NÃO pushar entre os dois lands (evita a janela vermelha
do smoke-install no CI).

**r6-P2 — segundo fator do controle positivo do parity aceita evidência
não-causal** (`smoke-install.yml:206`: `PLANTED` imprime na montagem do
plant e `per-mode verdicts` em todo run completo; um rc=1 por causa alheia
passa). ACEITO como classe real (registered-vacuous, S292), **DEFERIDO com
causa**: o fator primário (rc exatamente 1) permanece; endurecer o grep
exige emendar `smoke-install.yml` em DOIS packs assinados encadeados (o 168
constrói sobre o conteúdo do 166 — mudar a camada de baixo invalida as
precondições da de cima). Vai para o próximo plano de manutenção como
"exigir marcador nomeado da divergência plantada no log do controle".

## Fechamento do rail

Rounds 1–5 (S296): 16 achados aplicados. Round 6: 1 confirmado-já-corrigido
(fora do pack) + 1 deferido com causa. **Zero achados novos contra o pack em
si** — encerrado; a assinatura do Owner (re-instanciação do sentinel com
anchor atual) é o V3 que autoriza o land.
