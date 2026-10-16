# rail-record — relmeta-143 (PLAN-194, RM da v1.4.3; molde sign-min): rodada única do patch, do texto e dos dados

Estado: ABERTO. Este arquivo foi commitado pelo construtor junto dos materiais, ANTES do rail, só com a forma
e os sha256 dos objetos que o rail vai revisar. O `Rail-Verdict` abaixo não é um veredito do molde: o P0 do
SIGN recusa qualquer valor fora de `APPROVE` e `DECLARED-P2`, então nada se assina com este registro. Quem
fecha o rail grava aqui, no commit que vira o `Anchor-SHA`, a saída das lanes e o veredito.

Rail-Subject: .claude/plans/PLAN-194/relmeta/relmeta.patch
Rail-Subject-sha256: e92ad0cad22446d3dc7bf305c2258fe1fa115d2d76f09447b2c89e4cb897b9bc
Rail-Sentinel: .claude/plans/PLAN-194/relmeta-approved.md
Rail-Sentinel-sha256: 9e981804475fb9c16bf82bb2e4ba16521d56ffa7b75c55930f27b8b2d8c0d484
Rail-Data: .claude/plans/PLAN-194/relmeta/sign.tsv
Rail-Data-sha256: 7fd50321fe0dbd4c10815bad13fac5f47c0e0726da099d4313b27294ffded770
Rail-Verdict: ABERTO

Informativos (o SIGN não os confere):

- Derivador `.claude/plans/PLAN-194/relmeta/apply-relmeta143-edits.py`: sha256 0a596fad834c4f718474c20edbe0544e66195fb284a5f3a6f6d20732793b7d09.
- Envoltório `.claude/plans/PLAN-194/relmeta/hard-relmeta.sh`: sha256 1777724f34602fcc760a92222a99d5e92743190d85f059553026b62772b2cc30.
- Registro do controle vermelho `.claude/plans/PLAN-194/relmeta/red-control.txt`: sha256 f564e7afb623ab3b75bd6b5d68fac4c8f6207ed917df016a7f409b065db19f05.
- Revisores, prompt, data e saída verbatim de cada lane: a preencher ao fechar a rodada.

## Rodada única do molde

- Lanes: o Codex 0.160.0 em `exec --sandbox read-only` e dois refutadores Claude, na MESMA rodada, com o
  derivador como terceira lane; no máximo uma conferência de anexo.
- Pauta: cada frase da headline contra a seção `[1.4.3]` do `CHANGELOG.md` e contra o código; cada âncora
  prova a frase e é vermelha na v1.4.2 (o `red-control.txt` é reproduzido); o `--verify` recusa escopo velho e
  land depois da derivação; o `Scope` do sentinel são os caminhos do patch; nenhuma frase fora do bloco comum
  do sentinel é falsa sobre o código, os dados ou o roteiro.
- Regra de parada pré-registrada: NO-GO só por condição falsa ou P0; correção re-deriva e re-commita os
  materiais, e só então este registro é preenchido.

## Saída das lanes

(a preencher)

## Triagem

(a preencher)
