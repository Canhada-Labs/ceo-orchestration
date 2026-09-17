---
id: PLAN-190-FOLLOWUP-relaunch-out-partial-write
title: "relaunch --out confere a escrita inteira (escrita parcial entregaria cópia truncada)"
status: draft
created: 2026-09-17
owner: CEO
depends_on: [PLAN-190]
level: L2
tags: [workflow, recovery, cli, followup]
---

## Context

Achado P2 da RODADA FINAL do pair-rail (r6) sobre a W1, declarado no anexo do sentinel assinado
(`.claude/plans/PLAN-190/w1/w1-approved.md`, commit `075beed9`) em vez de abrir outra volta de revisão,
pela regra «rodada final com anexo» que o Owner ratificou em 10/09/2026.

`_write_new_file` em `.claude/scripts/ceo-launches.py` cria o destino com
`O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` (nunca sobrescreve, nunca segue symlink) e depois faz **um único**
`os.write(fd, data)`. `os.write` pode escrever MENOS bytes do que o buffer; o rail reproduziu injetando
um retorno de 2 para 11 bytes. Hoje isso devolve sucesso e deixa no disco uma cópia TRUNCADA do snapshot
do script — exatamente o material que o rito de recuperação manda passar como `scriptPath`.

## Goal

`relaunch --out` ou entrega o arquivo com os bytes completos, ou falha nomeando o erro e NÃO deixa
arquivo incompleto no disco.

## Items

### W1 — escrita completa ou nada  [P1]  (livre: `.claude/scripts/ceo-launches.py` não é canônico)
- Laço até escrever todos os bytes (ou `os.writev`/`write` repetido), tratando `InterruptedError`.
- Qualquer falha no meio: remover o arquivo que ESTA operação criou (só ele — o `O_EXCL` garante que o
  arquivo é nosso) e devolver rc 2 com o motivo.
- Regressão em `.claude/hooks/tests/test_check_workflow_launch.py`: `os.write` que devolve menos bytes
  (monkeypatch no módulo) ⇒ rc 2, mensagem nomeando a escrita parcial, arquivo AUSENTE ao fim; e o
  caminho feliz continua entregando bytes idênticos ao snapshot.
- Prova por mutação: reverter o laço ⇒ a regressão fica vermelha.

## Regra de parada
- Se a cura exigir mudar o contrato do `relaunch` (rc, formato de saída) além de uma linha de erro nova,
  parar e tratar como wave própria do PLAN-190 — este follow-up é uma correção de escrita, não um
  redesenho da recuperação.
