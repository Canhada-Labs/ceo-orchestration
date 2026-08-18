---
id: PLAN-180
title: "Propagação da doutrina token-as-time (ADR-081): validador advisory, eta_calendar e prompts de vendor"
status: draft
created: 2026-08-16
level: L2
owner_approval: pending
related_adrs: [ADR-081 (token-as-time-unit — este plano EXECUTA o Step 3 deferred), ADR-020 (cache discipline), ADR-058 (debate budget)]
related_plans: [PLAN-060 (origem do ADR-081), PLAN-179 (precedente de draft sob freeze)]
budget_tokens: 60-105k (W0 30-50k; W1 10-20k; W2 10-20k; W3 10-15k)
budget_sessions: 1
context_risk: low
external_wait: "W3 apenas: 1 assinatura GPG do Owner (sentinel cobre ADR-081 amend + council.md). Gate de execução: autorização do Owner — freeze rota-SEQUÊNCIA ativo (S304); nada aqui toca superfície de release, então autorização pré-tag é possível (precedente: PLAN-178)."
eta_calendar: "mesma sessão para W0-W2 após o gate liberar; W3 = +1 pinentry do Owner no mesmo dia. Sem external_wait ⇒ entrega = mesmo-dia."
---

# PLAN-180 — Propagação da doutrina token-as-time (ADR-081)

## Objetivo

Fechar os 3 gaps que fazem estimativas em "semanas/dias humanos"
reaparecerem nos planos e debates, apesar do ADR-081 (ACCEPTED
2026-04-25) ter estabelecido tokens+sessões como unidade canônica.
Correção verbatim do Owner (S62, repetida em 2026-08-16/S310):
"para de dar prazo humano a coisas que o claude resolve em minutos".

## Contexto / evidência (levantada S310)

1. **Adoção do frontmatter está OK** — 100% dos planos 152→179 têm
   `budget_tokens`/`budget_sessions`/`context_risk`/`external_wait`.
2. **Gap A — a doutrina não viaja.** Zero menção ao ADR-081 na skill
   `ceo-orchestration` (Gate 2), em `.claude/commands/debate.md` e nos
   prompts de spawn (`inject-agent-context.sh`). Codex/Grok/subagentes
   nunca veem a regra ⇒ re-contaminam debates com "semanas".
3. **Gap B — validador nunca construído.** ADR-081 Step 3
   (`check-time-unit.py`, advisory) ficou deferred;
   `enforcement_commit: pending` desde abril. Corpos vazam:
   PLAN-153:397 "adds ~1-2 weeks wall-clock", PLAN-172:66 "estende
   2 semanas" (este é external-wait legítimo — o validador precisa
   distinguir).
4. **Gap C — falta o ETA de calendário.** Tokens/sessões respondem
   "cabe na sessão?", não "quando fica pronto?" — a pergunta que o
   Owner usa para planejar. Empiria do repo: trabalho puramente-CEO
   completa mesmo-dia a D+1 (PLAN-177 e PLAN-178: 1 dia cada);
   calendário só estica por `external_wait`.

## Waves

### W0 — `check-time-unit.py` (executa ADR-081 Step 3) — 30-50k

- `.claude/scripts/check-time-unit.py` (~50-80 LoC, stdlib-only,
  py≥3.9, `from __future__ import annotations`).
- Varre planos/ADRs **novos** (data de criação ≥ 2026-04-25 no
  frontmatter, ou lista de arquivos passada em argv) por vocabulário
  de tempo-humano usado como ESFORÇO: `semanas?`, `weeks?`,
  `dev-dias?`, `dias? (úteis)?`, `horas de trabalho`, `sprints? de`,
  `meses`, fora de contextos legítimos.
- **Whitelist de contexto legítimo** (não flagra): linha dentro de
  `external_wait:`, e vocabulário de espera externa — soak, hold,
  SLA, deprecation/EOL, retention, janela de telemetria/observação
  ("por 30 dias" de coleta é espera, não esforço).
- **Advisory-only**: exit 0 sempre; achados em stdout com
  `path:linha: trecho`. Wire em `validate-governance.sh` como soft
  check (não bloqueia — coerente com fail-open em infraestrutura).
- Teste-espelho na convenção vigente (Tier-1 sem teste-espelho =
  red silencioso — memória S286); usar `TestEnvContext` se tocar env.
- AC-W0.1: rodado contra o corpus atual, flagra PLAN-153:397 e NÃO
  flagra PLAN-172:66 (external-wait) nem "hold 24h"/"soak 7d" —
  esse par é o controle positivo E negativo do validador.

### W1 — `eta_calendar:` no PLAN-SCHEMA — 10-20k

- `PLAN-SCHEMA.md` (caminho livre, não-canônico): novo campo
  recomendado `eta_calendar:` na seção ADR-081, com REGRA DE
  DERIVAÇÃO explícita:
  `eta_calendar = max(external_waits) quando houver; senão
  "mesma sessão" (budget_sessions=1) ou "mesmo-dia a D+1"
  (multi-sessão)`.
- Documentar a empiria que sustenta a regra (177/178 = 1 dia cada).
- AC-W1.1: exemplo completo no schema; PLAN-180 (este arquivo) já
  carrega o campo — é o primeiro dogfood.

### W2 — Propagação em caminhos livres — 10-20k

- `.claude/commands/debate.md` (livre): bullet no template de prompt
  das rodadas — "estimativas de esforço em tokens+sessões (ADR-081);
  prazo humano SÓ para external_wait; converta qualquer 'semanas de
  trabalho' recebido de vendor externo antes de consolidar".
- `.claude/scripts/inject-agent-context.sh` (livre): mesma linha na
  seção fixa do prompt gerado — cobre TODOS os spawns nomeados.
- AC-W2.1: grep pós-edit mostra a citação ADR-081 nos dois
  geradores; um prompt gerado de amostra contém o bullet.

### W3 — Cerimônia (Owner GPG, 1 sentinel) — 10-15k

- Amend do frontmatter de `ADR-081`: `enforcement_commit: <sha do
  W0>` (fecha o "pending" de abril). Path canônico.
- `.claude/commands/council.md` (canônico, egress-guarded): mesmo
  bullet do W2 nos prompts das lanes externas.
- Sentinel ÚNICO cobrindo os 2 paths; pode pegar carona em qualquer
  cerimônia já agendada. Se o Owner preferir, W3 é destacável — W0-W2
  entregam o valor principal sozinhos.
- NÃO tocar a skill `ceo-orchestration` (cache-estável Gate-2 +
  SP-NNN/soak 7d): a propagação via debate/spawn/council já cobre
  quem estima. Se telemetria pós-W0 mostrar vazamento residual do
  próprio CEO, abrir SP-NNN pela rota normal — fora deste plano.

## Riscos

- **Falso-positivo do validador** em espera legítima → mitigado pela
  whitelist + advisory-only (nunca bloqueia; precedente ADR-081 Step 3
  "not blocking").
- **Freeze rota-SEQUÊNCIA**: nenhuma wave toca superfície de release
  (scripts de release, workflows CI, SPEC, installer). Ainda assim,
  execução gated na autorização do Owner.
- **Regex de vocabulário escrito de memória** erra nos dois sentidos
  (memória: conjuntos fechados devem ser derivados) → o AC-W0.1
  ancora o validador em pares reais do corpus, não em vocabulário
  imaginado.

## How to continue

Sessão nova: Gate 1-2, ler este plano, confirmar autorização do Owner
(gate de execução no frontmatter). Executar W0→W1→W2 na mesma sessão;
W3 quando houver pinentry disponível. Commit por wave com hint
`feat(PLAN-180 W<n>): ...`. Ao final: `status: done`, backfill
`related_commits`, atualizar memória `project-time-unit-adr081-gaps.md`.
