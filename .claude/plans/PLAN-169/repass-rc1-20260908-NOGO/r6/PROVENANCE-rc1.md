# Proveniencia do re-pass do CANDIDATO v1.4.0-rc.1 - PLAN-169 - 6 partes
- Base: v1.3.0 (ec0543b615c4621e259a409e9eace951539a6632 -> d789721c2fd4a11c36c87eda0e1118eab59092e4) .. Candidato: 861ee97f09cdf8660d955b20d206bad8ea3f5ec4 (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- codex: 0.147.0 / aarch64-apple-darwin / payload 19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37
- modelo: gpt-5.6-sol (explicito via -m; a config global pede gpt-6-astra, fora do alcance da CLI pinada)
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.md sha256 87c895f887cc585876793ca90c1565882d356ffb112e24052c621686484d7bd8
- Data: 2026-09-09T00:53:41Z
- parte 1 (upgrade.sh — o caminho que roda na arvore do adopter): VERDICT: NO-GO — O digest novo da geração v1.3 ativa um refresh que pode alterar um inode hard-linked fora do alvo, e essa P1 não está curada nem declarada no envelope. [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: c07142e2cdd2ae41deeaa4b7d2a5d03bae14a8255a6e81568139a805ae368270
- parte 2 (install.sh + o set de manifesto + a tabela de rotas de entrega): VERDICT: NO-GO — o envelope atual omite três falhas P1 concretas e precisa ser emendado e reassinado, ou os caminhos devem ser curados, antes do corte da rc.1. [codex rc=0]
  - payload-rc1-2.raw.txt NAO commitado; pin sha256: 1467d8c6dfa01af3340dec11b8d3d47ff0d8dba72e5fb3799a30239ef27f18d6
- parte 3 (doctor.sh + uninstall.sh + templates/** entregues): VERDICT: NO-GO — Condition 16 is materially false, and the unconfined restore-aside path is a missing P1 from the proposed signed conditions. [codex rc=0]
  - payload-rc1-3.raw.txt NAO commitado; pin sha256: d84475c4152afa985ed74ca69d68d00a5a7928765a470f07955f2004c82c03c5
- parte 4 (SPEC/** + npm README + CHANGELOG + settings.json + workflows entregues): VERDICT: NO-GO — Before rc.1, correct the two contradictory CHANGELOG claims and close the ceremony-lint discovery fail-open, which the proposed envelope does not declare. [codex rc=0]
  - payload-rc1-4.raw.txt NAO commitado; pin sha256: ab20a29929070cc91f0f07cfe34f45a13e665cc74d168004f03753684a023437
- parte 5 (hooks da familia de continuidade de compaction): VERDICT: NO-GO — The signed draft omits the false-ABSENT memory classification and unconstrained hook-delivery write, both P1 conditions for this rc.1. [codex rc=0]
  - payload-rc1-5.raw.txt NAO commitado; pin sha256: e94df6d329370ef5cfd10e4e6dc969792f0911b50f914967b25868ccf8203370
- parte 6 (nucleo de cadeia e auditoria em _lib/): VERDICT: NO-GO — The proposed envelope omits a P1 destructive ownership claim over pre-existing files in the newly selected native state directory. [codex rc=0]
  - payload-rc1-6.raw.txt NAO commitado; pin sha256: a9f29c6a8b78ac5be984ce6a37ea4a4c03ed1c77b67ab34c195e265e8405e90f
RUNNER-OVERALL: rc=1
