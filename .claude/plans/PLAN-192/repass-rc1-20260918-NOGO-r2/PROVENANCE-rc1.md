# Proveniencia do re-pass do CANDIDATO v1.4.1-rc.1 - PLAN-192 - 3 partes
- Base: v1.4.0 (23b79ddae2253d33ed5aa643bc094fe1e7a3deb7 -> f9db82ecdfaa677e3eaa803743a35087dca227c8) .. Candidato: 3ed81cf657b3d22d012b1e32269671e86f3e4030 (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- Caminhos pessoais (/Users/<dono>, /home/<dono>, -Users-<dono>) substituidos por <user> no diff antes do payload e em transcript/verdict depois do codex (cura 1 do gate de contaminacao; rodada 17)
- codex: 0.155.0 / aarch64-apple-darwin / payload b0b14f9c1901c1ec44671094b2dc18b39e4bd8d36a6dc2302cc9d961a7e2a197
- rota do codex: binario global (versao pinada, payload verificado)
- modelo: gpt-6-astra (explicito via -m; origem: config.toml do codex (tabela raiz))
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.reviewed.md sha256 822b4d74699819df313579bb2f9ef6a169d28c008effdb7261adcb330d789f8e
- Data: 2026-09-18T23:30:01Z
- parte 1 (check_workflow_launch.py + _lib/launch_ledger.py — o hook PreToolUse/PostToolUse que roda na sessao do adopter a cada chamada da tool Workflow, e o ledger que ele grava): VERDICT: GO-WITH-CONDITIONS [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: 927615ffc330ce47d133807945e07a21e585e2dded9f66e2669f55789c396b89
- parte 2 (registracao e entrega: settings.json do dogfood, templates/settings/** (base e o perfil user derivado), build-plugin.py, env-inventory, CHANGELOG, INSTALL/README, npm/ e os sitios de versao do bump): VERDICT: NO-GO — Condition 14 still promises inode-safe cleanup that the check-then-unlink implementation does not guarantee. [codex rc=0]
  - payload-rc1-2.raw.txt NAO commitado; pin sha256: eade602a2fb3753e6da7330e84407726577ba669f3553015530628860df771ab
- parte 3 (as CLIs: ceo-launches.py (a rota que a mensagem de bloqueio nomeia) e as cinco de recuperacao/aprovacao, mais os dois docs de operador): VERDICT: GO-WITH-CONDITIONS — Under the stated cut rule, retain the applicable declared conditions and these new findings in the signed advisory material. [codex rc=0]
  - payload-rc1-3.raw.txt NAO commitado; pin sha256: a25b8be3f1b094a3befd2204d79751c5a4111b1f7ed0ac842524f50daa663230
RUNNER-OVERALL: rc=1
