# Proveniencia do re-pass do CANDIDATO v1.4.2-rc.1 - PLAN-193 - 4 partes
- Base: v1.4.1 (36da3e77181a0676b433d8364ca68c68f739d9f3 -> 50fab7556961950967668f3af8e3ca6f7a0cf474) .. Candidato: 9b5b1b40078c20e6de4806d89cabd5776a7d33df (PRE-tag; base resolvida no run)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- Caminhos pessoais (/Users/<dono>, /home/<dono>, -Users-<dono>) substituidos por <user> no diff antes do payload e em transcript/verdict depois do codex (cura 1 do gate de contaminacao; rodada 17)
- codex: 0.156.1 / aarch64-apple-darwin / payload 0196e89fe5a7598f816ee54232c3d7c26d75e502ab5cfe2c9240e81d90f7255a
- rota do codex: binario global (versao pinada, payload verificado)
- modelo: gpt-6-astra (explicito via -m; origem: config.toml do codex (tabela raiz))
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.reviewed.md sha256 939918694f1bc1495bd0953065fde18a208b446befaa1435410cbf0cc7fc2e2f
- sonda das condicoes: verde (18 linhas OK, nenhuma FALSA; probe-rc1.txt)
- base assinada por: AE9B236FDAF0462874060C6BCFCFACF00335DC74
- Data: 2026-09-29T02:06:38Z
- parte 1 (instalacao, upgrade e settings entregues: templates/** (settings base e user, .mcp.json, codex/), .claude/settings.json, scripts/ (install.sh, upgrade.sh, install-accelerators.sh e o resto do instalador), o piso VETO e o pin efetivo (_lib/agent_frontmatter.py, _lib/effective_config.py), env-inventory, CHANGELOG/INSTALL/SUPPORT/README, npm/ e os sitios de versao do bump): VERDICT: GO-WITH-CONDITIONS — Payload 1 satisfies the stated cut rule with the applicable declared conditions, carried debt, and mandatory 24-hour hold; this is advisory evidence, not authorization. [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: 9d98a895d4e7e819fb9eabc1cc962fdd837d91f4836dd7a490c9c8fd84017d77
- parte 2 (os hooks que rodam na sessao do adopter - o adapter live, o audit_log, o hook PreToolUse/PostToolUse da tool Workflow e o ledger que ele grava - e a recuperacao que eles nomeiam: ceo-launches.py (relaunch --out) e docs/workflow-recovery.md; e a camada de isolamento da suite pytest (_lib/test_isolation.py, cujo Eixo 4 poe um claude FALSO no PATH da suite)): VERDICT: GO-WITH-CONDITIONS — Applicable conditions are honest and sufficient under the stated rc.1 rule, with the mandatory 24-hour hold and declared debt retained. [codex rc=0]
  - payload-rc1-2.raw.txt NAO commitado; pin sha256: a781207acc28f25ac0c5f3e7e99c8f94ab78e09f49c4626af7c69a6425d8929d
- parte 3 (as CLIs e a documentacao: .claude/scripts/** (precos e telemetria, tier-policy, otimizador, detectores, ceo-boot, benchmark de skills, o validate-governance.sh, check-substrate-drift.py, derive-settings-baselines.py), .claude/commands/**, .claude/skills/** e docs/**): VERDICT: GO-WITH-CONDITIONS — Under the stated cut rule, retain the applicable declared conditions, include both P1 findings in the signed annex, and preserve the mandatory 24-hour hold. [codex rc=0]
  - payload-rc1-3.raw.txt NAO commitado; pin sha256: b108d58554811d14d26a08da477a33dba0b4cce78bd93cf93cd33d555da4cc59
- parte 4 (re-pin-codex.py - o gerador do pack de re-pin do Codex CLI (ADR-182) - e os dois docs da adocao de substrato e de modelo novo (docs/adopter-new-model-fast-access.md, docs/substrate-adopt-2026-09.md)): VERDICT: GO-WITH-CONDITIONS — Retain conditions 1–2 and 9–12, include the new P1 in the signed annex, and observe the mandatory 24-hour hold; this review is advisory evidence, not authorization. [codex rc=0]
  - payload-rc1-4.raw.txt NAO commitado; pin sha256: 928af053b7140ba280bbb973ea61ddd848c205f73c85b2de79f54ba6f75b522b
RUNNER-OVERALL: rc=0
