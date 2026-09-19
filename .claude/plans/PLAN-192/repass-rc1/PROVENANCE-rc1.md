# Proveniencia do re-pass do CANDIDATO v1.4.1-rc.1 - PLAN-192 - 3 partes
- Base: v1.4.0 (23b79ddae2253d33ed5aa643bc094fe1e7a3deb7 -> f9db82ecdfaa677e3eaa803743a35087dca227c8) .. Candidato: 7602fbe46318a77f1f8740f81d5b08ef5080df94 (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- Caminhos pessoais (/Users/<dono>, /home/<dono>, -Users-<dono>) substituidos por <user> no diff antes do payload e em transcript/verdict depois do codex (cura 1 do gate de contaminacao; rodada 17)
- codex: 0.155.0 / aarch64-apple-darwin / payload b0b14f9c1901c1ec44671094b2dc18b39e4bd8d36a6dc2302cc9d961a7e2a197
- rota do codex: binario global (versao pinada, payload verificado)
- modelo: gpt-6-astra (explicito via -m; origem: config.toml do codex (tabela raiz))
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.reviewed.md sha256 8177f65d81ac366dc5829ebcd4f5e6623339d703c034248d7c87c0e024eb38b0
- Data: 2026-09-19T00:49:18Z
- parte 1 (check_workflow_launch.py + _lib/launch_ledger.py — o hook PreToolUse/PostToolUse que roda na sessao do adopter a cada chamada da tool Workflow, e o ledger que ele grava): VERDICT: GO-WITH-CONDITIONS — This payload satisfies the stated cut rule with the applicable declared conditions, the additional P1 in the signed annex, and the mandatory 24-hour hold. [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: 24de40e3c6a7903c36eea30d7a459ae55bdb72313efeef0c645e0e293edadf8a
- parte 2 (registracao e entrega: settings.json do dogfood, templates/settings/** (base e o perfil user derivado), build-plugin.py, env-inventory, CHANGELOG, INSTALL/README, npm/ e os sitios de versao do bump): VERDICT: GO-WITH-CONDITIONS — The applicable disclosures are honest and sufficient under the stated rc.1 rule, with the mandatory 24-hour hold and known-open findings retained in the signed material. [codex rc=0]
  - payload-rc1-2.raw.txt NAO commitado; pin sha256: b2f1c6bf839c5052eec83a7afbee97ecbb3b699deb7d077336a9c2e2b56e0d3e
- parte 3 (as CLIs: ceo-launches.py (a rota que a mensagem de bloqueio nomeia) e as cinco de recuperacao/aprovacao, mais os dois docs de operador): VERDICT: GO-WITH-CONDITIONS — Retain the applicable conditions and this annex in the signed prerelease material, with the mandatory 24-hour hold; this review is advisory evidence only. [codex rc=0]
  - payload-rc1-3.raw.txt NAO commitado; pin sha256: 93ccd0ac306dc418a956ea5a69924617f218cd6bbee9dac766a5606682705af0
RUNNER-OVERALL: rc=0
