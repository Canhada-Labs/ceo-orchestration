# Proveniencia do re-pass do GA v1.4.0 (promocao da v1.4.0-rc.1) - PLAN-169 - 7 partes
- Base: v1.3.0 (ec0543b615c4621e259a409e9eace951539a6632 -> d789721c2fd4a11c36c87eda0e1118eab59092e4) .. Candidato: 168d29124439c186d3dd29e848d711d86481f209 (PRE-tag GA; arvore da rc.1 + cura de calendario + kit do GA)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- Caminhos pessoais (/Users/<dono>, /home/<dono>, -Users-<dono>) substituidos por <user> no diff antes do payload e em transcript/verdict depois do codex (cura 1 do gate de contaminacao; rodada 17)
- codex: 0.147.0 / aarch64-apple-darwin / payload 19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37
- modelo: gpt-5.6-sol (explicito via -m; a config global pede gpt-6-astra, fora do alcance da CLI pinada)
- condicoes declaradas no prompt (DATA para o revisor): CONDITIONS-ga.reviewed.md sha256 71bea5f07c7123b9759a660141f488154997c24defc81a85792d3422bb14b3d3
- Data: 2026-09-14T01:00:28Z
