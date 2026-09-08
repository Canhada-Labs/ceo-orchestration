# Proveniencia do re-pass do CANDIDATO v1.4.0-rc.1 - PLAN-169 - 6 partes
- Base: v1.3.0 (ec0543b615c4621e259a409e9eace951539a6632 -> d789721c2fd4a11c36c87eda0e1118eab59092e4) .. Candidato: 6b3ab79f6d69508d7eea2a5089b41c0a412f6879 (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- codex: 0.147.0 / aarch64-apple-darwin / payload 19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37
- modelo: gpt-5.6-sol (explicito via -m; a config global pede gpt-6-astra, fora do alcance da CLI pinada)
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.md sha256 7f0dd2513413039c07a09e58697074e6305a8a0460bdd72b774a2f8f3207b12c
- Data: 2026-09-08T03:41:12Z
- parte 1 (upgrade.sh — o caminho que roda na arvore do adopter): VERDICT: GO-WITH-CONDITIONS — Ampliar a condição 4 e acrescentar a exceção de `_up_tmpbase`; não há P0/P1 novo que bloqueie a rc.1. [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: 82e33a8feeef2f557b604d29d39c26586eefe20a93757d1ae5d0296e48be1751
- parte 2 (install.sh + o set de manifesto + a tabela de rotas de entrega): VERDICT: NO-GO — Conditions 5 and 7 materially understate implemented ownership behavior and must be corrected in the signed envelope, or fixed in code, before rc.1. [codex rc=0]
  - payload-rc1-2.raw.txt NAO commitado; pin sha256: 2230b612d330bc37458c34e8a981529c5dc916b84d890302b3203b13ec7a13a4
- parte 3 (doctor.sh + uninstall.sh + templates/** entregues): VERDICT: NO-GO — The envelope omits the uninstall parser’s fail-open completion bug and the absent Codex pre-push backstop, both P1 gaps that must be fixed and positively tested before rc.1. [codex rc=0]
  - payload-rc1-3.raw.txt NAO commitado; pin sha256: 668cabc8e11a0da4d62d769d031bc3f670e8bba0bdfdd916b1c963f5c128001f
- parte 4 (SPEC/** + npm README + CHANGELOG + settings.json + workflows entregues): VERDICT: NO-GO — The rc.1 envelope omits the promised active-state cutover condition, while the scoped CHANGELOG and CI workflow retain two additional P1 honesty gaps. [codex rc=0]
  - payload-rc1-4.raw.txt NAO commitado; pin sha256: 2599ee70ba2cad3364fc189a6c8bafaf5c666463cc31e920fd7d64d98da0dd62
- parte 5 (hooks da familia de continuidade de compaction): VERDICT: NO-GO — The signed draft omits the required v1.3 state migration, contains false audit and GC assertions, and misses a second P1 reinjection source. [codex rc=0]
  - payload-rc1-5.raw.txt NAO commitado; pin sha256: 35af27b57dfed29b40fb8cda9c7c34edcf035bc45d39361b87b9acd420ffdaef
- parte 6 (nucleo de cadeia e auditoria em _lib/): VERDICT: NO-GO — o envelope contém uma afirmação falsa e omite condições P1 necessárias para uma atualização v1.3.0→rc.1 auditável. [codex rc=0]
  - payload-rc1-6.raw.txt NAO commitado; pin sha256: 2bba5285ffecc93ec04591009bec274c246baee8bc1e52ee7de9381372b9b469
RUNNER-OVERALL: rc=1
