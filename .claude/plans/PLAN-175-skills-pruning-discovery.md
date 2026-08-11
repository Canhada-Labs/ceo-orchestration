---
id: PLAN-175
title: Skills — descoberta antes de poda: unknown-ratio <0.10, core 42→~25, domain-packs opt-in, contagem derivada
status: draft
created: 2026-08-11
owner: CEO
depends_on: [PLAN-171]
budget_tokens: 150-300k (firmado S302e; passo 3 migração é o grosso)
budget_sessions: 2-4 (passo 1 = 1; passos 2-3 = 1-2; passo 5 = 1)
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
   **ativada se após a re-medição da Fase 1 o unknown-ratio ainda
   for ≥ 0,10 (critério pela META, não por queda relativa — r2:
   queda de 50% pararia em ~0,21 e mascararia o alvo).**
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
4. **Sweep de atualidade — EXECUTA no W-IM do PLAN-172 (dono único;
   r2 P1: sem rota dupla).** Este plano fica com a REGRA permanente:
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

## 3. Pronto-para-execução (S302e)

**ACs por passo:** P1 = mecanismo de sugestão vivo com positive
control (spawn sem skill ⇒ sugestão aparece no transcript) + baseline
do unknown-ratio publicado com inputs (janela 90d, N≥100) **+ (r4) a
re-medição obrigatória aos 30d publicada E a decisão de Fase 2
APLICADA pela regra do §1 (ratio ≥0,10 ⇒ fail-high ativado; <0,10 ⇒
registrado como atingido) — P1 não fecha no baseline.** P2 = lista
de arquivamento DERIVADA pela regra determinística (nunca curada à
mão) + `archive/` restaurável testado (1 skill arquivada e restaurada
no mesmo PR de teste). P3 = 116 domain movidos p/ packs assinados
(squad-install), 1-2 domínios de referência em-tree, CI verde sem os
packs; AC-mestre: install/upgrade de adopter SEM packs funciona
(smoke). P5 = superfícies de claim derivadas ("N core + M frontend +
packs opt-in"); AC: `check-claude-md-claims` verde com tolerance=0
após a mudança.

**Dependências verificadas:** PLAN-171 W1c (contrato de fronteira)
antes do P3; sweep de atualidade EXECUTA no W-IM/172 (dono único).

**Runbook sessão 1:** ligar telemetria/sugestão (P1) + medir
baseline. Nada de poda na sessão 1 — por design.

**Debate:** Codex r1→r3 (GO no r3); `/debate start PLAN-175` no
início da execução; a poda em si passa pelo processo SP-NNN/soak.
