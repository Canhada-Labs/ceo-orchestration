# Proveniencia do re-pass do CANDIDATO v1.4.0-rc.1 - PLAN-169 - 6 partes
- Base: v1.3.0 (ec0543b615c4621e259a409e9eace951539a6632 -> d789721c2fd4a11c36c87eda0e1118eab59092e4) .. Candidato: 2b1d259da8b747c7c2ac740555db47cfde9ea80f (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- codex: 0.147.0 / aarch64-apple-darwin / payload 19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37
- modelo: gpt-5.6-sol (explicito via -m; a config global pede gpt-6-astra, fora do alcance da CLI pinada)
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.md sha256 13cce8c187bc4db0064f0a6e32d292cbeeae0356bcaa9cc18503c3fed0526581
- Data: 2026-09-08T17:41:23Z
- parte 1 (upgrade.sh — o caminho que roda na arvore do adopter): VERDICT: NO-GO — Antes do rc.1, o envelope precisa cobrir a fonte ausente no checkout corrente e tornar suficientes as condições operacionais 42 e 43. [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: cbbbef855065109a4ce056f3a151ae396ae1d5ee1b25c23da8c36613f7e0f59e
