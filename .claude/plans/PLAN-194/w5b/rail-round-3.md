# rail-round-3 — W5b do PLAN-194 (rodada ÚNICA da migração para o molde sign-min: texto do sentinel e dados)

Rail-Round: 3
Rail-Subject: .claude/plans/PLAN-194/w5b/w5b.patch (inalterado desde a rodada 2), .claude/plans/PLAN-194/w5b-approved.md (reescrito para o molde) e .claude/plans/PLAN-194/w5b/sign.tsv (novo)
Rail-Subject-sha256: 6c691139e1c9a048b4c1b1a66586a7271d1d7e4902cd3e6b8f66319fee513bf1
Rail-Sentinel-sha256: 8fa5244e2debecf6233d10352b3d6ba0098c44bfed5a96fd439d8a28b715138a
Rail-Data-sha256: 78c5bd18b78e88b818f7200ab304edfff7d58761c1592bc703795da40e5e406c
Rail-Reviewer: PENDENTE (rodada única pela D2: Codex read-only e 2 refutadores Claude na mesma rodada)
Rail-Date: PENDENTE
Rail-Reviewer-Verdict: PENDENTE
Rail-Verdict: PENDENTE
Rail-Findings: PENDENTE

O patch é o mesmo das rodadas 1 e 2 (sha256 igual ao do `Rail-Subject-sha256` de `rail-round-2.md`). Esta
rodada revisa o que a migração para o molde `.claude/plans/PLAN-194/sign-min/` mudou: o texto do sentinel
(cabeçalho com `Dados`/`Molde`, bloco comum, «Controle vermelho (registro)», bateria própria, resíduos) e os
dados do pacote. O `Rail-Sentinel-sha256` é o do sentinel com os quatro campos por preencher; o
`Rail-Data-sha256`, o do `sign.tsv`.

Checklist da rodada (SPEC do molde, §14 item 6):
- nenhum gate do SIGN anterior do pacote sumiu: os genéricos estão na lista fixa do molde, os específicos
  são linhas `hard` dos dados;
- o controle vermelho do `red-control.txt` é reproduzido sobre as pré-imagens (D1);
- toda frase própria do pacote no sentinel é verdadeira no código.

## Saída do revisor

(PENDENTE)

## Triagem

(PENDENTE)

## P2 declarados

(PENDENTE)
