# Proveniencia do re-pass do CANDIDATO v1.4.0-rc.1 - PLAN-169 - 6 partes
- Base: v1.3.0 (ec0543b615c4621e259a409e9eace951539a6632 -> d789721c2fd4a11c36c87eda0e1118eab59092e4) .. Candidato: 5518888545c4b987524f315626d2f98ef996b91e (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- codex: 0.147.0 / aarch64-apple-darwin / payload 19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37
- modelo: gpt-5.6-sol (explicito via -m; a config global pede gpt-6-astra, fora do alcance da CLI pinada)
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-rc1.md sha256 dd39a1455924ecbde254e974d7bd9e9897ed10d5b603fd7ae7548ace3ea76bd4
- Data: 2026-09-08T13:13:25Z
- parte 1 (upgrade.sh — o caminho que roda na arvore do adopter): VERDICT: NO-GO — O envelope está factualmente desatualizado e o fail-closed da tabela ainda aceita symlink laundering e destinos duplicados. [codex rc=0]
  - payload-rc1-1.raw.txt NAO commitado; pin sha256: 8ee4739113a5fe3b36bdb044c65006725fe72be02c5ae6072424c08fac71124e
- parte 2 (install.sh + o set de manifesto + a tabela de rotas de entrega): VERDICT: NO-GO — O envelope contém condições falsas e omite P1s de confinamento e validação da tabela que precisam ser corrigidos ou declarados com precisão antes da rc.1. [codex rc=0]
  - payload-rc1-2.raw.txt NAO commitado; pin sha256: 13390571df94137669332b344e8378970e743119e1fcec12d6d7c2496badf0fb
- parte 3 (doctor.sh + uninstall.sh + templates/** entregues): VERDICT: NO-GO — Condition 16 is false as signed, and the uninstaller has undeclared fail-open paths that must be fixed and positively tested before rc.1. [codex rc=0]
  - payload-rc1-3.raw.txt NAO commitado; pin sha256: 56521c40e6a2b568a56f34e726f46fee1783177726ccb382bbb3c08949583d79
- parte 4 (SPEC/** + npm README + CHANGELOG + settings.json + workflows entregues): VERDICT: NO-GO — Condition 23 omits a P1 attribution gap affecting three newly registered audit actions, so the proposed signed rc.1 envelope is not yet truthful. [codex rc=0]
  - payload-rc1-4.raw.txt NAO commitado; pin sha256: 360d7e36fe6b80c6a6f43a9d0fa0613f577b7a3726fbe03f5f66a44d5254e46b
- parte 5 (hooks da familia de continuidade de compaction): VERDICT: NO-GO — A condição 18 não é material assinável honesto e sua cura de symlink não confina os ancestrais. [codex rc=0]
  - payload-rc1-5.raw.txt NAO commitado; pin sha256: a0a951e5cfbd9ebb63b095661c9059e28a01e278a2f1bcf89ca7fb2da5db1744
- parte 6 (nucleo de cadeia e auditoria em _lib/): VERDICT: NO-GO — The envelope omits two decision-bearing state migrations, and conditions 21 and 23 prescribe cures that do not satisfy the current code paths. [codex rc=0]
  - payload-rc1-6.raw.txt NAO commitado; pin sha256: eaabe02bb685daf48293809bdad5fd5a4918ec42bb0941f01b067c8b8af0fabb
RUNNER-OVERALL: rc=1
