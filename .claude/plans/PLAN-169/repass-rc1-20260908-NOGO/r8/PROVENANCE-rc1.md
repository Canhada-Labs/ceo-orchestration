# Proveniencia do re-pass do CANDIDATO v1.4.0-rc.1 - PLAN-169 - 6 partes
- Base: v1.3.0 (ec0543b615c4621e259a409e9eace951539a6632 -> d789721c2fd4a11c36c87eda0e1118eab59092e4) .. Candidato: cd087048684956843fe9592600ea56ee45a95ab6 (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- codex: 0.147.0 / aarch64-apple-darwin / payload 19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37
- modelo: gpt-5.6-sol (explicito via -m; a config global pede gpt-6-astra, fora do alcance da CLI pinada)
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.md sha256 919773da8e5224a3a07a879ec3ab239ea559375207e53bc58272c9b03d0a6d93
- Data: 2026-09-09T10:48:01Z
- parte 1 (upgrade.sh — o caminho que roda na arvore do adopter): VERDICT: NO-GO — O envelope atual omite dois P1 que permitem, respectivamente, um upgrade parcial sem estado final e uma entrega incompleta registrada como sucesso. [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: b0e49cb34966325819dd0775898883576bb050376500a39c02ae6da466ad3076
- parte 2 (install.sh + o set de manifesto + a tabela de rotas de entrega): VERDICT: NO-GO — Antes da rc.1, a condição 5 precisa ser corrigida e a aceitação de registro malformado por `_codeowners_provenance` precisa ser curada ou declarada como condição DURA precisa. [codex rc=0]
  - payload-rc1-2.raw.txt NAO commitado; pin sha256: e03e5d1a1e735250b40c2cca52eb65bfaeccae8bd8d67297ce2bc8718989c842
- parte 3 (doctor.sh + uninstall.sh + templates/** entregues): VERDICT: NO-GO — The envelope contains a false hard condition and omits a newly introduced blocking behavior in the advertised user profile. [codex rc=0]
  - payload-rc1-3.raw.txt NAO commitado; pin sha256: 12825578aa0ead2977a3ee740d701838575d663833c2203f375d3c65141fcc59
- parte 4 (SPEC/** + npm README + CHANGELOG + settings.json + workflows entregues): VERDICT: NO-GO — Condition 58 is demonstrably false and the shipped CHANGELOG makes an unimplemented restore-safety promise, so this candidate is not yet sufficient for rc.1 even with the proposed signed envelope. [codex rc=0]
  - payload-rc1-4.raw.txt NAO commitado; pin sha256: 2c2dc13b5c11829d40fa6d0e4724bcfccfacfce7e8c959110752a1b5600fb700
- parte 5 (hooks da familia de continuidade de compaction): VERDICT: NO-GO — The declared payload-5 conditions are accurate, but they omit four P1 conditions required for an honest and sufficiently constrained rc.1 envelope. [codex rc=0]
  - payload-rc1-5.raw.txt NAO commitado; pin sha256: 2081ac17e23117b113933a278d93e2d85647f895163443e83f0744c44d886ff4
- parte 6 (nucleo de cadeia e auditoria em _lib/): VERDICT: NO-GO — O envelope omite duas falhas P1 de concorrência que podem quebrar a nova cadeia HMAC por projeto sem adulteração. [codex rc=0]
  - payload-rc1-6.raw.txt NAO commitado; pin sha256: 04a47c207dee7f0588a8815196939fb281de1741a95924cb7b451cb280d68f32
RUNNER-OVERALL: rc=1
