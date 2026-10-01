---
plan: PLAN-195
round: 1
labels:
  Critic-A: vp-engineering
  Critic-B: threat-detection-engineer
  Critic-C: security-engineer
purpose: registro de auditoria do protocolo anonymize-before-synthesis (DEBATE-SCHEMA §13.2)
---

# Rodada 1 — mapa de anonimização

A síntese (`consensus.md`) consome só o texto anonimizado das críticas; os nomes de
persona e de arquétipo não entram nela. Este mapa é o registro de auditoria.

| Rótulo | Arquivo da crítica | Arquétipo | Veredito | VETO |
|---|---|---|---|---|
| Critic-A | `vp-engineering.md` | VP Engineering | ADJUST | não (o papel não tem VETO) |
| Critic-B | `threat-detection-engineer.md` | Principal Threat Detection Engineer | ADJUST | sim, de escopo estreito (cobertura, FPR, operabilidade), condicional aos must-fix 1–4 |
| Critic-C | `security-engineer.md` | Principal Security Engineer | ADJUST | sim, condicional aos must-fix 1–9 no plano e no rascunho da ADR-201 |

Observação: o frontmatter de `threat-detection-engineer.md` traz `generated_at:
2026-09-30T21:35:00Z`, que é a hora LOCAL (-03) rotulada como UTC; o arquivo foi
escrito por volta de 2026-10-01T02:47Z. O texto da crítica não foi alterado.
