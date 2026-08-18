---
plan: PLAN-181
round: 1
created_at: 2026-08-17T23:05:00-03:00
---

# PLAN-181 — Proposta para debate (round 1)

> Plano completo: `.claude/plans/PLAN-181-loop-governed-adoption.md`
> Estudo de origem (S310): memória `project-s310-loop-adoption-study.md`;
> workflow `wf_5e8e8ab8-dda` (4 lanes + síntese).

## Tese

O `/loop` do harness nunca foi usado neste repo, mas
`docs/AUTONOMOUS-LOOP-GUIDE.md` JÁ prescreve `/loop 24h /nightly-hygiene`
como rota native-autonomy-first — prescrição jamais executada (mesma classe
do achado "skills 157/164 zero-uso" da S302b). /loop é **Tier-C nato**
(ADR-125:211-236) com um único kill-switch (`CLAUDE_CODE_DISABLE_CRON`) e
ZERO das salvaguardas ADR-133 (opt-in auditado, budget, teto de iterações,
audit por tick, pausa Owner-absent). Veredito do estudo: **adotar com
wrapper, nunca cru**.

## Decisões propostas (o que o debate deve atacar)

1. **W0 — piloto ASSISTIDO (vigia do hold 24h):** no próximo trem RC→GA,
   Owner PRESENTE, `/loop 1h` read-only que checa janela do hold via exit
   code de script (nunca julgamento do modelo) e notifica quando abrir.
   LINHA DURA: o loop JAMAIS corta tag/executa GA-CUT/landa. Transcript
   arquivado com ticks + tokens/tick.
   **Fato novo pós-autoria:** na S311/S312 o hold da rc.4 foi vigiado por um
   `Monitor` (tool nativa, evento-driven, `ls-remote` a cada 5min) — funcionou
   (0 falsos, encerrou sozinho no fim do hold). O debate deve responder:
   o W0 via /loop ainda agrega o quê sobre o Monitor? (candidato: /loop
   exercita ScheduleWakeup/recorrência que o Monitor não cobre.)
2. **W1 — inventário $0:** hook Stop advisory que loga `session_crons` no
   audit-log (evento novo HMAC-chained; bump do schema SPEC — superfície
   canônica); sonda do ScheduleWakeup dinâmico em sessão descartável.
3. **W2 — skill `/loop-governed`:** wrapper fechando os 7 gaps, cada um com
   molde existente: opt-in auditado (molde night-mode: fail-closed, REFUSE
   em CI, registro duplo), budget por tick (`cost_envelope.py`, hard cap
   single-strike), teto de iterações + detector de não-progresso (mesma
   classe de achado em 2 ciclos = parar — lição S296), audit por tick,
   auto-PAUSE >12h sem Read do Owner, proibição de tocar governança
   (Gate-1/hooks/ADR/SPEC), contexto fresco (estado em disco, re-ancoragem
   por ciclo — converge com PLAN-179 Constraint Pinning).
   Primeiro consumidor real: ciclo `nightly-proposals.py` ->
   `morning_ledger.py` ($0, ratificação Owner-only).
4. **W3 — debate + cerimônia:** SKILL.md nova = canônica => sentinel GPG;
   §Cost do ADR-125 é condição de ship.

## Honestidades já declaradas

- NÃO reivindicar tamper-evidence de execution-context entre iterações
  (HMAC RESERVED, zero produtores — ADR-133:166-182).
- Interação delay×TTL de cache: F(Gate1+2)~45-55k re-pagos se o cache
  expirar entre ticks — documentar, não esconder.
- Wrapper pode virar teatro (checagem que avisa e `return 0`) — lição t10:
  toda detecção nova exige RECUSA + controle positivo que prove a recusa.

## Perguntas abertas para os críticos

- OQ-1: W0 ainda vale a pena dado que o Monitor já provou o caso vigia?
  Reescopar W0 para o que SÓ o /loop exercita?
- OQ-2: os 7 gaps de W2 são o conjunto certo? Falta algum? (ex.: interação
  com night-mode/acceptEdits — um loop rodando sob acceptEdits herda
  autonomia de escrita?)
- OQ-3: o wrapper como SKILL é o mecanismo certo (advisory por natureza —
  MECHANISM-SELECTION.md) para gaps que são de ENFORCEMENT (budget, teto)?
  O que exige hook?
- OQ-4: sequência W1 antes de W2 — o evento de inventário sem consumidor é
  sonda órfã (classe E4 do PLAN-179)?
- OQ-5: quem é o dono do custo recorrente (tokens/tick) e onde o relatório
  aparece para o Owner?
