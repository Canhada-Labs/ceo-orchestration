---
id: PLAN-171-FOLLOWUP-cost-envelope-emit
parent: PLAN-171
title: O evento cost_envelope_capped nunca é gravado — action duplicado no emit_generic (achado da W0 do PLAN-171)
status: draft
created: 2026-10-10
owner: CEO
depends_on: [PLAN-171]
tags: [audit, hooks, canonical, followup]
---

## Context

Achado da W0 do PLAN-171 (registro do pai, entrada de 2026-10-02), conferido
por leitura em 2026-10-10:

- `.claude/hooks/check_cost_envelope.py:198-207` chama
  `emit_generic("cost_envelope_capped", action="cost_envelope_capped", …)`.
- A assinatura é `emit_generic(action: str, **kwargs)`
  (`.claude/hooks/_lib/audit_emit.py:5238`). O `action` chega duas vezes, e o
  Python levanta `TypeError`.
- O `except Exception` de `check_cost_envelope.py:208-209` engole o erro. O
  bloqueio acontece, mas o evento `cost_envelope_capped` nunca entra na cadeia.
- A ação já está registrada (`audit_emit.py:390` e `:5739`). A cura não
  precisa mudar o SPEC.
- O teste de bloqueio da W0 (`test_check_cost_envelope_block.py`) declara o
  defeito e não afirma a emissão, para não travar o defeito como contrato.

## O pacote de código JÁ ESTÁ EM CURSO — este plano não o duplica

Na S363 foi construído um pacote canônico mínimo para este defeito, proposto
para o lote B de assinaturas do trem 1.4.3 (PLAN-194). Estado em 2026-10-10:
commits locais, NÃO landados no `main`.

- `5cf80e2d`: a cura (uma linha a menos no `check_cost_envelope.py`) e
  `.claude/hooks/tests/test_check_cost_envelope_emit.py`.
- `b8e87e47`: a docstring do teste de bloqueio passa a dizer a verdade depois
  da cura.
- `3edf44dc`: o teste da emissão fixa que `project` é o envelope e que as
  chaves do chamador ficam fora da linha.

Este arquivo existe para o achado da W0 ter dono no disco depois que o PLAN-171
fechou. O trabalho de código é o do pacote acima. Pela recomendação 3 da síntese
de fechamento da S363, o pacote entra no lote só se o rail convergir em até 2
rodadas; senão, vai para a 1.4.4.

## Goal

Um bloqueio do `check_cost_envelope.py` grava o evento `cost_envelope_capped`
na cadeia HMAC, com teste que fica vermelho sem a cura.

## Items

### W1 — land do pacote em curso  [P1]  (canônico: cerimônia GPG)
- Nada a construir aqui. Acompanhar o pacote até o land ou até a decisão de
  levá-lo à 1.4.4.

## Success criteria

- [ ] A cura está no `main`, e o teste da emissão fica vermelho sem ela (controle registrado no pacote).
  Check: `python3 -m pytest -q .claude/hooks/tests/test_check_cost_envelope_emit.py`
