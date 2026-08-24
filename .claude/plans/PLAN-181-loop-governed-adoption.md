---
id: PLAN-181
title: "Adoção governada do /loop do harness: piloto assistido + wrapper /loop-governed (Tier-C compliant)"
status: reviewed
reviewed_at: 2026-08-18
reviewed_by: "Owner — flip draft→reviewed autorizado na S313 (2026-08-18) após debate L3 round-1 (S312, round_verdict PROCEED, 3× ADJUST/0 VETO; emendas r1-C1..C3 e demais aplicadas inline no corpo). O consensus.md condicionava o flip à revisão do Owner — cumprida. GA v1.3.0 saiu 2026-08-17; W0 (piloto) só roda em CLONE com tag falsa (emenda C3), nunca num hold real."
created: 2026-08-16
level: L3
owner_approval: "reviewed-gate granted S313 (2026-08-18); execução W0-W3 ainda exige a autorização de execução do Owner por sessão (W3 = /debate + 1 GPG)"
related_adrs: [ADR-133 (autonomous-loop opt-in doctrine — molde das salvaguardas), ADR-125 (Tier-C: §Cost obrigatório), ADR-103 (hold 24h — alvo do piloto), ADR-081 (unidade tokens)]
related_plans: [PLAN-135 (W4 D3 inventário session_crons), PLAN-165 (night-mode — molde de opt-in auditado), PLAN-179 (Constraint Pinning — re-ancoragem por ciclo)]
budget_tokens: 120-220k (W0 piloto 20-40k; W1 inventário 20-40k; W2 wrapper 60-100k; W3 debate+cerimônia 20-40k)
budget_usd_estimate: "~$16-30 total (o ~$8-15 do §Cost derivava de F=50k, refutado; reescalado por 97.292/50.000 = 1,95 — S325)"
tier_mix_estimate: "sonnet ~90% / opus ~10% (opus só nos debates L3)"
tier_mix_rationale: "tick mecânico é sonnet; Haiku proibido sem torneio (ADR-052); opus reservado ao debate, que é onde a decisão mora"
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

### W0 — Piloto em ENSAIO: recorrência do /loop em clone — 20-40k
### [REESCRITA pelo debate r1 — C3: W0 JAMAIS roda num hold real]

- **[Emenda r1-C3]** O piloto roda em **CLONE com tag falsa** (doutrina
  S293/S301), nunca no repo vivo nem acoplado a um release. Objetivo
  reescopado: exercitar o que SÓ o /loop tem (recorrência /
  ScheduleWakeup / cron do harness) — o caso "vigia de hold" pertence ao
  `Monitor` por doutrina (AUTONOMOUS-LOOP-GUIDE:24) e foi provado
  superior na S311/S312 (processo externo, sem modelo, sem escrita).
- **[Emenda r1-C1]** A dispensa "Owner presente" NÃO existe no ADR-125
  (grep zero). Ou o piloto é estritamente $0 de modelo (script + exit
  codes), ou exige o opt-in Tier-C completo. Nenhuma wave roda antes da
  seção §Cost deste plano existir.
- **[Emenda r1-C8]** PRIMEIRO AC do plano inteiro: controle positivo do
  kill-switch `CLAUDE_CODE_DISABLE_CRON` (loop de brinquedo em sessão
  descartável; provar que o tick seguinte NÃO dispara; medir latência
  até a parada). Kill-switch reprovado ⇒ veredito do plano vira NÃO
  ADOTAR. Adicionar kill-file em disco (env não atravessa sessões).
- LINHA DURA (mantida, agora com mecanismo): o ensaio nunca toca repo
  vivo; se algum dia um loop rodar perto de um freeze, a linha dura
  exige matcher PreToolUse fail-closed (git tag/push/gh release) com
  controle positivo da RECUSA — prosa não é mecanismo (lição S303).
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

### W2 — `/loop-governed` como COMPOSIÇÃO (comando + script canonical + hook) — 60-100k (orçamento a rever: hook novo = ADR + cerimônia)
### [REESCRITA pelo debate r1 — C4/C5: skill não entrega enforcement]

> **[Emenda r1-C4]** MECHANISM-SELECTION.md:63 marca recurring-scheduled
> como Skill ❌; o próprio molde night-mode é comando+script+guard+deny,
> zero skill. W2 entrega: `.claude/commands/loop-governed.md`
> (superfície) + `.claude/scripts/loop_governed.py` (lógica, adicionada
> ao `_CANONICAL_GUARDS`) + **hook novo** para budget/teto/proibição de
> governança (enforcement; cerimônia GPG + ADR próprio). Skill, se
> existir, carrega SÓ doutrina. Guard de `.claude/commands/**` por
> CLASSE, não por instância.
> **[Emenda r1-C5]** Os trilhos atuais são CEGOS ao tick
> (`check_cost_envelope` = matcher Bash + assinatura de coordinator;
> `check_budget` = matcher Agent; `is_disabled()` passthrough sem
> `CEO_SWARM=1`). Cada gap da tabela DECLARA seu ponto de interceptação
> (evento de hook + comportamento na recusa + controle positivo da
> recusa). W2.2 nomeia `CEO_SWARM`/`class_tier`/janela `per_plan` por
> `loop_id`. **[Emenda r1-C6]** A medição "quais eventos de hook um tick
> dispara" (AC de W1) é BLOQUEANTE de W2.
> **[Emenda r1-C10]** Tier do tick nomeado: `model: sonnet` (Haiku
> proibido sem torneio; herança de Opus é o trap A3). Números no corpo:
> W0 ≈ $4,6-5,5/piloto (cache sempre frio — 60min > TTL); nightly ≈
> $0,19-0,23/dia com dono nomeado (OQ-5: FinOps no fechamento de trem;
> nightly reporta no morning_ledger).

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
| **W2.8 [Emenda r1-C2]** | **Composição com posture de permissão** | tick-0 lê a posture EFETIVA e RECUSA fail-closed se `acceptEdits`/`bypassPermissions`/`dontAsk`/`auto` (enum derivado da autoridade, nunca de memória); controle positivo da recusa; simetricamente `night-mode on` recusa com cron/loop vivo |
| **W2.9 [Emenda r1-B]** | **Fronteira de identidade** | o tick roda com credenciais do Owner (git/gh/GPG-agent) — declarar exclusão explícita: tick JAMAIS assina (gpg), JAMAIS pusha; matriz de composição loop×night-mode×swarm×Workflow com combinações proibidas |

- **[Emenda r1-C9]** Estado inter-tick: allowlist de campos estruturados
  (nunca prosa livre), releitura tratada como UNTRUSTED (fenced + capped,
  mesma postura do retorno inter-agente), `CEO_UNICODE_HARDBLOCK=1`
  durante o loop. W2.6 implementada em HOOK (prosa de skill decai 30-59%
  sob compactação — PLAN-179) e ordenada APÓS o Constraint Pinning do
  179. W2.5 só é entregável com sinal de atribuição HUMANA real (o proxy
  `session_start` é auto-fabricável) — senão declarar NÃO-ENTREGUE.
  W2.3 exige CHAVE DE CLASSE mecânica para "mesma classe de achado".
  Eventos novos landam COM consumidor na mesma wave; W1 sonda o SHAPE de
  `CronSummary` antes do bump de SPEC e loga só derivados (contagem,
  intervalo, sha256 do prompt — nunca o corpo). Máx 1 loop governado por
  projeto (envelope compartilhado sem atribuição) até existir
  atribuição por `loop_id`. Modo degradado (INFRA no meio de loop
  não-atendido): decidir explicitamente fail-open padrão vs exceção
  ADR-186. Checar `CEO_SOTA_DISABLE` no tick-0 e recusar.
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

## Cost (ADR-125:230-236 — condição de QUALQUER wave; emenda r1-C1)

- **(a) Tokens por invocação/tick:** W0-ensaio (clone): alvo $0 de modelo
  (script + exit codes); se um tick de modelo existir: **~F frio 97.292
  MEDIDO** (mediana 98.636, max 138.552, pstdev 16.148 — série n=41; o
  `45-55k` que esta linha citava foi **REFUTADO** na S322 e é ~1,95× menor
  que a realidade) + ~1-2k out por tick (cache sempre frio quando
  delay > TTL).
  Nightly (W2, 1 tick/dia): mesmo perfil frio, `model: sonnet`.
- **(b) Cap diário de burn — RECALCULADO na S325, porque o número
  refutado da alínea (a) DECIDIA este cap.** Escalando o próprio $/tick
  deste plano pelo `F` medido (97.292 / 50.000 = 1,946 sobre o ponto médio
  da faixa antiga): $0,22 × 1,946 ≈ **$0,43/tick** ⇒ 24 ticks ≈
  **$10,27/dia**; na cauda (max-`F` 138.552 / 50.000 = 2,771) ≈ $0,61/tick
  ⇒ **$14,63/dia**. Portanto: piloto **≤ $11/dia** (F-mediano), com cap de
  cauda **≤ $15/dia** se o gate não puder falso-disparar; nightly
  **≤ $0,70/dia**. **O cap antigo era um falso-disparo esperando
  acontecer:** `≤ $6/dia` estoura por volta do tick **14 de 24** mesmo com
  `F` MEDIANO, e o `≤ $0,50/dia` do nightly estoura na cauda ($0,61) — o
  single-strike teria parado o loop em execuções SAUDÁVEIS e isso seria
  lido como estouro real. Estouro = single-strike: loop PARA e notifica.
- **(c) Mecanismo de enforcement:** hook novo (W2) chamando
  `cost_envelope.check_and_record(cents, plan_id=<loop_id>)` na janela
  `per_plan`, com decisão EXPLÍCITA de `CEO_SWARM`/`class_tier`
  registrada no ADR do W2 (`is_disabled()` faz passthrough sem
  `CEO_SWARM=1` — sem essa decisão o cap nunca avalia: teatro t10).
- Frontmatter **completado na S325** (a dívida real: o flip para
  `reviewed` aconteceu em 2026-08-18 e as três chaves nunca entraram —
  `grep -cE '^(budget_usd_estimate|tier_mix_estimate|tier_mix_rationale):'`
  dava **0**). Os valores estão no frontmatter deste arquivo;
  `budget_usd_estimate` foi reescalado de `~$8-15` para `~$16-30` pelo
  mesmo fator 1,95 da alínea (b), porque a estimativa antiga derivava de
  `F = 50k`.
- Dono do custo recorrente (OQ-5): LLM FinOps Architect revisa
  tokens/tick no fechamento de cada trem; nightly reporta no
  `morning_ledger.py`.

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
