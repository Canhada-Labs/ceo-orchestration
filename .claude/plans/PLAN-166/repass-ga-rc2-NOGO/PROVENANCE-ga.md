# Proveniencia do re-pass GA (hold ADR-103) - v1.3.0 - 2 partes
- Base: v1.2.0 .. Tag: v1.3.0-rc.2 (0cb09c3cc587abdeaed33e0ff13b1c8b3677061d)
- Worktree detached da TAG: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- Data: 2026-08-10T23:37Z
- parte 1 (version/docs/config surfaces + adopter upgrade path): VERDICT: NO-GO [codex rc=0]
  - payload-ga-1.raw.txt NAO commitado; pin sha256: 89c2947115e79a37bd6ce3ff1881c3caf5911dc839cdc8d982abbd866ae72869
- parte 2 (executable release machinery (workflows, driver, tag guard, bump sites, npm await-gate, step-15 validator)): VERDICT: NO-GO — An obsolete workflow run can still publish the wrong tag tree, creating an irreversible P1 GA risk. [codex rc=0]
  - payload-ga-2.raw.txt NAO commitado; pin sha256: 8a73022e31e41dc03494e26afae5cb423c26e64790ec18cd076bf6109c8a628b
RUNNER-OVERALL: rc=1
