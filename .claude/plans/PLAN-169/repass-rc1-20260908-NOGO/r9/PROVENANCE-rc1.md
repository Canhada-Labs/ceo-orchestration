# Proveniencia do re-pass do CANDIDATO v1.4.0-rc.1 - PLAN-169 - 6 partes
- Base: v1.3.0 (ec0543b615c4621e259a409e9eace951539a6632 -> d789721c2fd4a11c36c87eda0e1118eab59092e4) .. Candidato: 67db62376261234d925c0e373f0daf0f367b9a25 (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- codex: 0.147.0 / aarch64-apple-darwin / payload 19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37
- modelo: gpt-5.6-sol (explicito via -m; a config global pede gpt-6-astra, fora do alcance da CLI pinada)
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.md sha256 1700915636062849783a57f11678ec2649ae907f83b44d1d4de881cef058fb02
- Data: 2026-09-09T13:31:29Z
- parte 1 (upgrade.sh — o caminho que roda na arvore do adopter): VERDICT: NO-GO — The signed envelope omits two P1 adopter hazards and must be corrected before rc.1 is cut. [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: c55a9d4da47260f475a8f5405f136b1945608bec12893f611eb72ff32d6d08c9
- parte 2 (install.sh + o set de manifesto + a tabela de rotas de entrega): VERDICT: NO-GO — A condição 61 ainda permite que proveniência malformada reative silenciosamente o CODEOWNERS e fornece uma mitigação incorreta para o opt-out deliberado. [codex rc=0]
  - payload-rc1-2.raw.txt NAO commitado; pin sha256: 6c6572c537197ecf15ed671dbab2c17f286116b065d7a8b1670efa58dfcee393
- parte 3 (doctor.sh + uninstall.sh + templates/** entregues): VERDICT: NO-GO — Condition 61 falsely credits the uninstaller with rejecting duplicate and symlinked manifests, leaving an undeclared P1 deletion path without `--force`. [codex rc=0]
  - payload-rc1-3.raw.txt NAO commitado; pin sha256: b9a329314f70d56af32e8054ed7e917066df57ba06ed1d225cf612428a1f3491
- parte 4 (SPEC/** + npm README + CHANGELOG + settings.json + workflows entregues): VERDICT: NO-GO — A P1 adopter-facing behavior contradiction is absent from the proposed signed conditions. [codex rc=0]
  - payload-rc1-4.raw.txt NAO commitado; pin sha256: 6343ed27658c89d2b316a04f49cf896428cd4fcacd29677ca7d65a7b286ec7a4
- parte 5 (hooks da familia de continuidade de compaction): VERDICT: NO-GO — O envelope contém uma condição P1 insuficiente e omite dois outros P1 que tornam a continuidade e a evidência forense falsas para caminhos legítimos de upgrade. [codex rc=0]
  - payload-rc1-5.raw.txt NAO commitado; pin sha256: a964ee480c7a0c4aa4b761936fd4162c04978b73887ffcc161afecbadbd08c15
- parte 6 (nucleo de cadeia e auditoria em _lib/): VERDICT: NO-GO — The signed envelope is missing the P1 ownership, file-type, and symlink precondition for the newly claimed `audit-key` path. [codex rc=0]
  - payload-rc1-6.raw.txt NAO commitado; pin sha256: e72c761cadbc88147f0cccc6ea2d4776374a8f4c9853cb5f264fd320c8cca32c
RUNNER-OVERALL: rc=1
