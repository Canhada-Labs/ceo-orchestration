---
id: PLAN-181
title: "Adoção governada do /loop do harness: piloto assistido + wrapper /loop-governed (Tier-C compliant)"
status: draft
created: 2026-08-16
level: L3
owner_approval: pending
related_adrs: [ADR-133 (autonomous-loop opt-in doctrine — molde das salvaguardas), ADR-125 (Tier-C: §Cost obrigatório), ADR-103 (hold 24h — alvo do piloto), ADR-081 (unidade tokens)]
related_plans: [PLAN-135 (W4 D3 inventário session_crons), PLAN-165 (night-mode — molde de opt-in auditado), PLAN-179 (Constraint Pinning — re-ancoragem por ciclo)]
budget_tokens: 120-220k (W0 piloto 20-40k; W1 inventário 20-40k; W2 wrapper 60-100k; W3 debate+cerimônia 20-40k)
budget_sessions: 2-3
context_risk: low
external_wait: "BLOQUEADO até GA v1.3.0 (freeze rota-SEQUÊNCIA S304 + decisão t10 do Owner pendente). W0 (piloto) só existe DURANTE um hold RC→GA ativo. W3 exige /debate (L3) + 1 GPG do Owner."
eta_calendar: "W0 = dentro do próximo hold 24h pós-tag; W1 = mesmo-dia pós-GA; W2-W3 = mesmo-dia a D+1 após debate. Sem hold ativo, W0 espera o próximo trem."
---

# PLAN-181 — Adoção governada do /loop do harness

## Origem

Estudo S310 (workflow `wf_5e8e8ab8-dda`, 4 lanes + síntese; memória
`project-s310-loop-adoption-study.md`). Fatos: o /loop do harness NUNCA
foi usado neste repo; `docs/AUTONOMOUS-LOOP-GUIDE.md` já prescreve
`/loop 24h /nightly-hygiene` como rota native-autonomy-first e a
prescrição nunca foi executada; /loop é Tier-C nato (ADR-125:211-236)
com um único kill-switch (`CLAUDE_CODE_DISABLE_CRON`) e zero das
salvaguardas ADR-133. Veredito do estudo: **adotar com wrapper, nunca
cru**. Sustentação acadêmica no relatório (Reflexion 2303.11366; Huang
2310.01798 — self-correction sem oráculo degrada; 2502.19559 — teto
2-4 + troca de alvo; 2505.06120 — contexto fresco + estado em disco).

## Waves

### W0 — Piloto ASSISTIDO: vigia do hold 24h (ADR-103) — 20-40k

- No próximo trem RC→GA, com o Owner PRESENTE (não é autonomia
  prolongada ⇒ não exige o opt-in Tier-C ainda): `/loop 1h` com prompt
  read-only — horas desde a tag + CI verde + preflight → quando a
  janela abrir, `PushNotification` ao Owner com o comando GA-CUT
  pronto → `stop: true`.
- LINHA DURA: o loop JAMAIS corta tag, executa GA-CUT ou landa
  qualquer coisa (freeze proíbe land entre tag e GA).
- AC-W0.1: transcript do piloto arquivado em `PLAN-181/pilot/` com
  contagem de ticks, tokens/tick e o timestamp da notificação.
- AC-W0.2: cada tick começa com check DETERMINÍSTICO (exit code de
  script, não julgamento do modelo) — doutrina "espere pelo ARTEFATO".

### W1 — Inventário $0: hook advisory de session_crons — 20-40k

- Hook (Stop) advisory-only que loga `session_crons` do input no
  audit-log (evento novo, HMAC-chained) — o inventário de loops vivos
  que o PLAN-135 W4 D3 já pede. Fail-open on infra.
- Fechar a sonda pendente do estudo: confirmar o comportamento
  cache-aware do ScheduleWakeup dinâmico (delay clamp, noop-streak)
  com um loop de brinquedo em sessão descartável.
- AC-W1.1: evento visível em `SPEC/v1/audit-log.schema.md` (bump de
  versão do schema) + teste-espelho do hook com `TestEnvContext`.

### W2 — Skill `/loop-governed` — 60-100k

Wrapper que fecha os 7 gaps da tabela do estudo (cada linha = 1 AC):

| AC | Gap | Mecanismo (molde existente) |
|---|---|---|
| W2.1 | Opt-in auditado | sentinel GPG + env flag exact-match (molde `night-mode.py`: fail-closed on input, REFUSE em CI, registro duplo) |
| W2.2 | Budget por tick/dia | acionar `_lib/cost_envelope.py` por tick; hard cap single-strike |
| W2.3 | Teto de iterações | max-iterações explícito + detector de não-progresso: mesma classe de achado em 2 ciclos ⇒ parar e escalar (lição S296) |
| W2.4 | Audit por tick | evento HMAC por wakeup (análogo a `swarm_iteration`) |
| W2.5 | Pausa Owner-absent | >12h sem Read do Owner ⇒ auto-PAUSE (molde `swarm_paused_owner_absent`) |
| W2.6 | Proibição de governança | tick jamais edita Gate-1 files, hooks/, ADRs, SPEC, cerimônia |
| W2.7 | Contexto fresco | estado durável em disco entre ciclos, nunca transcript acumulado; re-ancoragem de objetivo por ciclo (converge com PLAN-179 Constraint Pinning) |

- HONESTIDADE: não reivindicar tamper-evidence de execution-context
  entre iterações (HMAC RESERVED, zero produtores até no swarm —
  ADR-133:166-182). Documentar a interação delay×TTL de cache
  (F(Gate1+2) ≈ 45-55k re-pagos se o cache expirar entre ticks).
- Primeiro consumidor real: ciclo `nightly-proposals.py` →
  `morning_ledger.py` (caso 1.1 do estudo — $0, ratificação
  permanece Owner-only).

### W3 — Debate + cerimônia — 20-40k

- `/debate start PLAN-181` (L3: skill nova que habilita autonomia
  recorrente). §Cost do ADR-125 é condição de ship.
- SKILL.md nova é superfície canônica ⇒ sentinel GPG (1 pinentry);
  rota SP-NNN se emendar skill existente.

## Riscos

- Piloto num hold real acopla o teste ao release ⇒ W0 é read-only
  estrito e o Owner está presente; falha do piloto não afeta o corte.
- Wrapper virar teatro (checagem que avisa e `return 0`) ⇒ lição do
  t10: toda detecção nova exige RECUSA + controle positivo que prove
  a recusa.
- Custo recorrente invisível ⇒ W2.2 + relatório de tokens/tick no
  próprio ledger do loop.

## How to continue

Sessão nova pós-GA: Gate 1-2, ler este plano + memória
`project-s310-loop-adoption-study.md`. Se houver hold ativo: W0.
Senão: W1 → W2 → W3. Commits `feat(PLAN-181 W<n>): ...`.
