# Proveniencia do re-pass do GA v1.4.1 (promocao da v1.4.1-rc.1) - PLAN-192 - 3 partes
- Base: v1.4.0 (23b79ddae2253d33ed5aa643bc094fe1e7a3deb7 -> f9db82ecdfaa677e3eaa803743a35087dca227c8) .. Candidato: 3b1419b94ccf21da25be87cf0a8c9994429ee52b (PRE-tag GA; arvore da rc.1 promovida)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- Caminhos pessoais (/Users/<dono>, /home/<dono>, -Users-<dono>) substituidos por <user> no diff antes do payload e em transcript/verdict depois do codex (cura 1 do gate de contaminacao; rodada 17)
- codex: 0.155.0 / aarch64-apple-darwin / payload b0b14f9c1901c1ec44671094b2dc18b39e4bd8d36a6dc2302cc9d961a7e2a197
- rota do codex: npx (cache proprio)
- modelo: gpt-6-astra (explicito via -m; origem: config.toml do codex (tabela raiz))
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-ga.reviewed.md sha256 a2cfafe7b65b882f5723a786c489d933010331ee8262c994810a350b570a4f63
- Data: 2026-09-28T13:50:15Z
- parte 1 (check_workflow_launch.py + _lib/launch_ledger.py — o hook PreToolUse/PostToolUse que roda na sessao do adopter a cada chamada da tool Workflow, e o ledger que ele grava): VERDICT: GO-WITH-CONDITIONS — This payload satisfies the stated cut rule with the named conditions and inherited findings remaining open. [codex rc=0]
  - payload-ga-1.raw.txt NAO commitado; pin sha256: d0f58e8f00597f6be3bd27b0a5f4ba4f577514253752bb0fc6c8fde5c23056bb
  - diff-ga-1.patch: sem mudanca na pathspec desde o candidato da rc.1 (7602fbe4)
- parte 2 (registracao e entrega: settings.json do dogfood, templates/settings/** (base e o perfil user derivado), build-plugin.py, env-inventory, CHANGELOG, INSTALL/README, npm/ e os sitios de versao do bump): VERDICT: GO-WITH-CONDITIONS — The applicable disclosures satisfy the stated GA cut rule, with all declared and carried findings remaining known-open. [codex rc=0]
  - payload-ga-2.raw.txt NAO commitado; pin sha256: 2f9ce2973d847d085133994ac69472ac40905dcac65b39d0d96ec058e6677237
  - diff-ga-2.patch: sem mudanca na pathspec desde o candidato da rc.1 (7602fbe4)
- parte 3 (as CLIs: ceo-launches.py (a rota que a mensagem de bloqueio nomeia) e as cinco de recuperacao/aprovacao, mais os dois docs de operador): VERDICT: GO-WITH-CONDITIONS — Under the stated cut rule, retain the applicable conditions and this new P1 annex in the signed advisory evidence; this verdict is not authorization. [codex rc=0]
  - payload-ga-3.raw.txt NAO commitado; pin sha256: 838e718de030730d5a8ca894c1ecc476c277aacc084b6fbaaf6b9af753e28557
  - diff-ga-3.patch: sem mudanca na pathspec desde o candidato da rc.1 (7602fbe4)
RUNNER-OVERALL: rc=0
