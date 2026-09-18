# Proveniencia do re-pass do CANDIDATO v1.4.1-rc.1 - PLAN-192 - 3 partes
- Base: v1.4.0 (23b79ddae2253d33ed5aa643bc094fe1e7a3deb7 -> f9db82ecdfaa677e3eaa803743a35087dca227c8) .. Candidato: 9e9840b2fc6c033498a0c12c65178a5254d0b04e (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- Caminhos pessoais (/Users/<dono>, /home/<dono>, -Users-<dono>) substituidos por <user> no diff antes do payload e em transcript/verdict depois do codex (cura 1 do gate de contaminacao; rodada 17)
- codex: 0.155.0 / aarch64-apple-darwin / payload b0b14f9c1901c1ec44671094b2dc18b39e4bd8d36a6dc2302cc9d961a7e2a197
- rota do codex: binario global (versao pinada, payload verificado)
- modelo: gpt-6-astra (explicito via -m; origem: config.toml do codex (tabela raiz))
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.reviewed.md sha256 e021623158d27549892276a2adb6e003fbd58a8c0e697dadb7c353c744ba2ebe
- Data: 2026-09-18T22:26:00Z
- parte 1 (check_workflow_launch.py + _lib/launch_ledger.py — o hook PreToolUse/PostToolUse que roda na sessao do adopter a cada chamada da tool Workflow, e o ledger que ele grava): VERDICT: NO-GO [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: 1cf86dc5844a15272d75ec037a6a8308f79fa295b42744275af888edc7f2b277
- parte 2 (registracao e entrega: settings.json do dogfood, templates/settings/** (base e o perfil user derivado), build-plugin.py, env-inventory, CHANGELOG, INSTALL/README, npm/ e os sitios de versao do bump): VERDICT: NO-GO — Condition 15 falsely excludes a release driver that the supported upgrade path delivers to adopters. [codex rc=0]
  - payload-rc1-2.raw.txt NAO commitado; pin sha256: 81ea123dcca3b6c90cf996ae9f974cf38c818090cba35b2e2d5b1ef8fc0b7931
- parte 3 (as CLIs: ceo-launches.py (a rota que a mensagem de bloqueio nomeia) e as cinco de recuperacao/aprovacao, mais os dois docs de operador): VERDICT: NO-GO — Declared condition B14 is false because `relaunch --out` can leave a partial destination file. [codex rc=0]
  - payload-rc1-3.raw.txt NAO commitado; pin sha256: 22a491d2842e3a8a8dba6aabe2a9a8ef7229060ee734747971db99e8e536e09b
RUNNER-OVERALL: rc=1
