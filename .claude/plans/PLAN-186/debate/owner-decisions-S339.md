---
plan: PLAN-186
recorded_at: 2026-09-02
recorded_by: CEO (AskUserQuestion, doutrina PLAN-135 K10 — texto da opção selecionada, verbatim)
---
# Decisões do Owner — S339 (2026-09-02)

| OQ | opção selecionada (verbatim) | efeito no plano |
|---|---|---|
| OQ-1 | «Fixar Fable 5.1 no pin já, sem A/B» | W2 (A/B do assento) sai do plano; o pin `model` do `settings.json` vai para `claude-fable-5-1` na cerimônia de roteamento |
| OQ-2 | «Rota (a): piso + migrar os agents (Recomendado)» | `claude-fable-5-1` entra em `VETO_FLOOR_ALLOWED` (dois ids na transição, fim após 1 wave sem violação); os 5 `agents/*.md` migram |
| OQ-3 | «Só em docs e derivações, nunca em código» | §2b: Sonnet 5 apenas para relatórios, docs e derivadores anchor-exact de TEXTO; qualquer `.py`/`.sh`/`.js`/`.yml` fica em Opus 5 |
| OQ-6 | «Tokens faturáveis dos transcripts, boot à parte (Recomendado)» | unidade normativa repo-wide = tokens faturáveis medidos pelo instrumento, com campo separado de gate-boot (F=97.292, faixa 47-147k); `PLAN-SCHEMA.md:324/328` curados em carona com FAIXA; planos antigos ganham nota de unidade legada |
| OQ-7 | «Wave própria depois da W1 (Recomendado)» | W0 entrega o censo das 4 superfícies; a tabela fonte-única papel→model id vira wave própria posterior à cerimônia de roteamento |
| OQ-8 | «≤ 1,3× o baseline pré-W4, medido localmente (Recomendado)» | AC-11 com instrumento próprio (`gh api` jobs × label do runner); PLAN-184 é «coordena com» |
| OQ-9 | «W1+W3 juntas, W4 separada (Recomendado)» | UMA cerimônia de roteamento (workflows `model:` + pins VETO/IC + piso + pin do assento) e UMA cerimônia de CI |
| Flip | «Sim, flipar para reviewed (Recomendado)» | após o round 3 confirmar e as decisões acima entrarem no plano: `status: reviewed`, `reviewed_by: Owner (S339, AskUserQuestion)` |
