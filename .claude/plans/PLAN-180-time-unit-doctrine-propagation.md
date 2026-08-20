---
id: PLAN-180
title: "Propagação da doutrina token-as-time (ADR-081): validador advisory, eta_calendar e prompts de vendor"
status: done
created: 2026-08-16
completed_at: 2026-08-18
related_commits: [4476acf, 996d72b, a2bd20e, 4b7efee, f182b01]
level: L2
owner_approval: "granted — S312 autorização de execução (W0-W2 landados 996d72b); W3 landado por cerimônia GPG S313 (4b7efee, sentinel PLAN-180/S313-approved.md); flip para done autorizado pelo Owner S313 2026-08-18"
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

## Registro de execução — W0-W2 (S312, 2026-08-18)

- **W0 ✓** `check-time-unit.py` (advisory, exit 0 sempre) + teste-espelho
  `scripts/tests/test_check_time_unit.py` (7 casos, herda TestEnvContext)
  + wire advisory no `validate-governance.sh` (WARN, nunca ERRORS;
  fail-open). AC-W0.1 provado nos DOIS sentidos contra o corpus real:
  flagra `PLAN-153-ecc-comparative-uplift.md:397` (o path do plano dizia
  "PLAN-153" — o arquivo real é o ecc), NÃO flagra PLAN-172 nem
  hold/soak. Calibração inicial errou nos dois sentidos como o §Riscos
  previu (4 defeitos achados rodando contra o corpus: whitelist
  acidental do próprio controle positivo, "por N semanas" de janela,
  meses de política de rotação, e o ADR-081 flagrando a si mesmo) —
  todos curados com o corpus como oráculo. Varredura inicial: 8 achados
  reais (vazamentos residuais documentados, ex. PLAN-171:195).
- **W1 ✓** `eta_calendar:` no PLAN-SCHEMA §3 com regra de derivação
  explícita + empiria (177/178 = 1 dia). Dogfood: este frontmatter.
- **W2 ✓** Bullet ADR-081 no template do `/debate` (item 5) e seção
  `## ESTIMATION DOCTRINE` incondicional no prompt do
  `inject-agent-context.sh` (cobre todos os spawns nomeados). AC-W2.1:
  grep 2/2 + prompt de amostra carrega o bullet.
- **W3 ✓ (S313, 2026-08-18, commit `4b7efee`, sentinel
  `PLAN-180/S313-approved.md`)** — carona no trem S313. Edit 1: ADR-081
  `enforcement_commit: 996d72b…`. Edit 2: bullet ADR-081 no `laneBrief`
  das lanes externas do **`.claude/workflows/council-audit.js`** — a nota
  W3 apontava `council.md`, mas o `.md` só delega ao workflow; o template
  do prompt externo vive no `.js`. Superfície corrigida; os 6 testes que
  tocam o arquivo verdes na simulação e no G4 do land.

## Registro de execução — follow-up do land W0-W2 (S313, mesmo commit `4b7efee`)

O land `996d72b` (W1: `eta_calendar` no PLAN-SCHEMA) mudou o
`PLAN-SCHEMA.md` sem apendar o hash da geração substituída à lista
hash-gated de `_refresh_schema_doc` em `scripts/upgrade.sh` — o refresh
PRESERVA a cópia antiga do adopter (v1.2.0/v1.3.0) e o parity e2e do
Smoke Install ficou vermelho (`FATAL [STALE]`, 2 modos) do `e5ce982` ao
`874117c`. Cura no mesmo trem S313: +1 hash (instância) + guard de classe
`scripts/tests/test-schema-generation-pins-unit.sh` (gerações derivadas de
git: release tags `v*` + histórico; zero gerações = exit 2) + wire no
`smoke-install.yml` (fetch de todas as tags v*, step, `paths:` com os 2
schema docs). Prova: parity e2e REAL PASS/STALE=0 no clone com o pack.
Lição: um contrato "apende o hash quando mudar o schema" que só vive em
comentário é a classe conjunto-fechado-de-memória — agora derivado do
git e vigiado por-PR.

## How to continue

Sessão nova: Gate 1-2, ler este plano, confirmar autorização do Owner
(gate de execução no frontmatter). Executar W0→W1→W2 na mesma sessão;
W3 quando houver pinentry disponível. Commit por wave com hint
`feat(PLAN-180 W<n>): ...`. Ao final: `status: done`, backfill
`related_commits`, atualizar memória `project-time-unit-adr081-gaps.md`.

## Disposição pós-done dos achados remanescentes (S316, 2026-08-20 — decisão do Owner)

O validador advisory (`check-time-unit.py`) ainda apontava 3 defeitos
vivos sem herdeiro após o fechamento deste plano. Disposição ratificada
pelo Owner em chat:

- **PLAN-153:397** — CURADO em S316: a opção (b) do OQ3 agora nomeia o
  ~1-2 weeks como espera externa de soak (ADR-081 external-wait), que é
  o que ele sempre foi.
- **PLAN-171:195** — CURADO em S316: a janela de replay agora é nomeada
  como janela de OBSERVAÇÃO retrospectiva de dados (7 dias-calendário),
  não estimativa de esforço.
- **ADR-080:168** — **WONTFIX registrado**: a linha é citação histórica
  de uma estimativa humana JÁ SUPERADA pelo próprio texto ("superseding
  the original ~3-5 dev-dias human-time"). Editar um ADR ACCEPTED para
  reescrever uma citação que documenta exatamente a transição de
  doutrina destruiria o registro da transição. O validador é advisory;
  este parágrafo é o registro do aceite.
