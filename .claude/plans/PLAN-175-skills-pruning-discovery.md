---
id: PLAN-175
title: Skills — descoberta antes de poda: unknown-ratio <0.10, core 42→~25, domain-packs opt-in, contagem derivada
status: draft
created: 2026-08-11
owner: CEO
depends_on: [PLAN-171]
budget_tokens: TBD no refinamento (estimativa grosseira 150-300k)
budget_sessions: 2-4
context_risk: low
external_wait: "gatilho: pós-GA v1.3.0; W1c do PLAN-171 (fronteira de ownership) primeiro"
tags: [skills, telemetry, pruning, seed]
---

# PLAN-175 — Skills: fechar a distância entre claim e realidade

> **SEMENTE (S302, 2026-08-11).** Da auditoria total: telemetria do
> skill-health sobre TODO o histórico mostra **157/164 skills com
> zero invocações (96%)** e **43,4% dos spawns nem resolvem para o
> catálogo** (labels ad-hoc). "166 skills ready-made" é a maior
> distância entre claim e realidade do repo. Não é gargalo de
> velocidade (reference-mode já evita custo por sessão) — é
> honestidade de catálogo e qualidade de roteamento.

## 1. Ordem de ataque (a ordem IMPORTA)

1. **Descoberta ANTES de poda — em duas fases (Codex r1: decisão
   tomada, não deixada em aberto):** Fase 1 = SUGESTÃO advisory
   (auto-suggest top-3 via skill-retrieve tf-idf) por 30 dias; Fase 2
   = fail-high APENAS para spawns que não declaram skill NENHUMA,
   ativada só se a Fase 1 não derrubar o unknown-ratio ≥50%.
   **Telemetria: janela = 90d de audit log, N mínimo = 100 spawns;
   re-medição 30d após cada fase.** Meta: unknown-ratio 0,43 → <0,10.
2. **Podar o core por telemetria — regra DETERMINÍSTICA:** arquivar
   skill core com 0 invocações em ≥90d E ausente do SKILL MAP;
   rollback = `archive/` restaurável + superfícies de contagem
   derivadas (nunca editadas à mão). 42 → ~25 (SKILL MAP + as usadas);
   ARQUIVAR, não deletar; consolidar sobreposições (lgpd×4 → 1;
   accessibility duplicada; 2 pares de basename duplicado que quebram
   atribuição de telemetria).
3. **Mover os 116 domain skills para squad-packs opt-in** via
   squad-install (tarball assinado — mecanismo já existe); manter 1-2
   domínios de referência em-tree. O repo recupera identidade de
   framework de governança; CI/soak param de vigiar prosa de domínio.
   Depende da fronteira de ownership (PLAN-171 W1c).
4. **Sweep de atualidade** (pode adiantar como imediato sem plano):
   skills core citando modelos mortos (gemini-1.5-pro, gpt-4-turbo,
   claude-3-opus) e codebase fantasma; apontar
   check-model-deprecations do nightly para `.claude/skills/`.
5. **Despinar o "166":** contagem DERIVADA ("N core + M frontend +
   packs opt-in") nas superfícies de claim — remove o incentivo
   estrutural anti-poda (hoje podar exige cascata de claims +
   cerimônia, então ninguém poda).

## 2. Guard-rails

- Poda passa pelo processo SP-NNN/soak existente — o gate de skills
  não é contornado, é usado a favor.
- Superfícies de contagem (CLAUDE.md, README, npm) mudam por
  derivação + verify-counts, nunca à mão (classe doc-count-drift é
  recidiva: 4/8 achados do último NO-GO).
- Telemetria continua ligada pós-poda: se unknown-ratio não cair com
  a descoberta (passo 1), o problema é o INJECTOR, não o catálogo —
  reavaliar antes do passo 2.
