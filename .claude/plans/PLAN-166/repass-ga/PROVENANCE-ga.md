# Proveniencia do re-pass GA (hold ADR-103) - v1.3.0 - 2 partes
- Base: v1.2.0 (abbb39eba5e5b83c7da6a817c4cf0ee033b5c266 -> 31c5026a37451a577cde8f60ed95306ee0cd8894) .. Tag: v1.3.0-rc.3 (ef90e9201790ed29a1b3f6f91ab7d357e65c5db0 -> 7362cfca026c1fd6b6cd780ff56329405ac91a25)
- Worktree detached da TAG: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- Data: 2026-08-12T19:08:42Z
- parte 1 (version/docs/config surfaces + adopter upgrade path): VERDICT: NO-GO — Three P1 findings require cure and re-pass before the stable tag is pushed. [codex rc=0]
  - payload-ga-1.raw.txt NAO commitado; pin sha256: 1948797768a9420b27f1520c017a553403e0be364ca055d5572cc4858eaa7a3c
- parte 2 (executable release machinery (workflows, driver, tag guard, bump sites, npm await-gate, step-15 validator)): VERDICT: NO-GO [codex rc=0]
  - payload-ga-2.raw.txt NAO commitado; pin sha256: 3c28f55a38176fb617cfcf804bc9385518ddc1a2e388bea3b80b978b9a5cd6a0
RUNNER-OVERALL: rc=1
