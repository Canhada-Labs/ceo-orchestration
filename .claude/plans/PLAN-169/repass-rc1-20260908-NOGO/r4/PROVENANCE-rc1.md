# Proveniencia do re-pass do CANDIDATO v1.4.0-rc.1 - PLAN-169 - 6 partes
- Base: v1.3.0 (ec0543b615c4621e259a409e9eace951539a6632 -> d789721c2fd4a11c36c87eda0e1118eab59092e4) .. Candidato: 144b0ef67ce4718890a6ded5652f4e0395fd00f6 (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- codex: 0.147.0 / aarch64-apple-darwin / payload 19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37
- modelo: gpt-5.6-sol (explicito via -m; a config global pede gpt-6-astra, fora do alcance da CLI pinada)
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.md sha256 b7652671db1fbf16608b0dcad9b1aebd0cce75cdec45c8b097abce61e17e60ac
- Data: 2026-09-08T16:13:56Z
- parte 1 (upgrade.sh — o caminho que roda na arvore do adopter): VERDICT: NO-GO — O envelope contém duas condições factualmente obsoletas e omite dois P1 adopter-facing: apropriação por mera igualdade histórica e escrita de backup fora do alvo. [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: e1a7c8e58c05977a68882f1762cde32240fd303852b8e4c55064eaed882a6b7a
