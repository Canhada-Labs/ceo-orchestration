# rail-record — relmeta-144 (PLAN-198, RM da v1.4.4; molde sign-min): ESQUELETO, preenchido só depois do rail

Rail-Subject: .claude/plans/PLAN-198/relmeta/relmeta.patch
Rail-Subject-sha256: a-preencher
Rail-Sentinel: .claude/plans/PLAN-198/relmeta-approved.md
Rail-Sentinel-sha256: a-preencher
Rail-Data: .claude/plans/PLAN-198/relmeta/sign.tsv
Rail-Data-sha256: a-preencher
Rail-Reviewer: a-preencher (rodada 1: codex-cli com a versão observada e o sha256 do payload registrados, pela rota de piso de versão da decisão OQ-2 do PLAN-198, em `exec --sandbox read-only`; dois refutadores Claude; o derivador como terceira lane)
Rail-Date: a-preencher
Rail-Reviewer-Verdict: a-preencher
Rail-Verdict: a-preencher
Rail-Findings: a-preencher

Informativos (o SIGN não os confere):

- Derivador `.claude/plans/PLAN-198/relmeta/apply-relmeta144-edits.py`: sha256 a-preencher.
- Envoltório `.claude/plans/PLAN-198/relmeta/hard-relmeta.sh`: sha256 a-preencher.
- Registro do controle vermelho `.claude/plans/PLAN-198/relmeta/red-control.txt`: sha256 a-preencher.
- Sujeito de cada rodada (o commit dos materiais revisado, e o `Derived-From` dele): a-preencher.
- Saídas verbatim, prompts e logs de cada lane: fora do repositório, na pasta de ferramentas do Owner da S366, com
  os sha256: a-preencher.

## Regra de parada (pré-registrada neste esqueleto, ANTES de qualquer rodada)

- Rodada 1, completa: o Codex, dois refutadores Claude e o derivador como terceira lane, na MESMA rodada, sobre
  os mesmos materiais commitados (o patch, o sentinel com os quatro campos por preencher, os dados, o derivador,
  o `hard-relmeta.sh` e o `red-control.txt`), re-derivados sobre a cadeia final (o último land fora do pacote é
  o `Derived-From`). Nenhuma lane sai antes das outras terminarem. Pauta mínima: cada frase da headline contra
  as seções `[1.4.4]` e `[1.4.3]` e o código, inclusive as frases sobre a condição 58 e as curas do anexo da
  v1.4.0 (os parágrafos 5 e 7 da headline).
- Rodada 2: a ÚLTIMA para código e afirmações (as âncoras do derivador e as frases da headline). Entre a
  rodada 1 e a 2, cada correção re-deriva e re-commita os materiais (`derive-relmeta144.sh`), e a rodada 2
  revisa os materiais re-commitados, não o delta.
- Depois da rodada 2, um achado abaixo de P0 só se cura estreitando ou removendo texto da headline (ou do
  título), sem frase nova de resultado no lugar, ou fica declarado na seção «Declarados» deste registro. Não há
  rodada 3 para código: um P0 depois da rodada 2 para o corte e volta ao CEO e ao Owner.
- NO-GO só por condição falsa ou P0; a correção re-deriva e re-commita os materiais, e só então este registro é
  preenchido. Um texto que mude depois da rodada 2 (por remoção) recebe uma conferência de refutador único só
  para P0/P1 sobre o delta, registrada aqui; ela não abre rodada.
- O `Rail-Verdict` que o SIGN aceita é `APPROVE` ou `DECLARED-P2`, escrito sem qualificação na linha própria.

## Rodada 1 (sujeito a-preencher)

a-preencher: a última mensagem do Codex, verbatim (com o VERDICT), e o resumo de cada lane Claude e do derivador.

## Rodada 2 (sujeito a-preencher)

a-preencher.

## Declarados (P2/P3 que ficam)

a-preencher.
