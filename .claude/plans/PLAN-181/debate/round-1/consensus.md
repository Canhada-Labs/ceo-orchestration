---
plan: PLAN-181
round: 1
round_verdict: PROCEED
verdicts: [Critic-A: ADJUST, Critic-B: ADJUST, Critic-C: ADJUST]
consensus_adjustments: 10
created_at: 2026-08-18T00:20:00-03:00
note: "PROCEED = design-coherent APÓS emendas §Emendas do plano (o redesenho de W0/W2 é substancial — o Owner revisa antes do flip para reviewed). NÃO autoriza ship; cascata V0-V3 intocada."
---

# PLAN-181 — Consenso round 1

3× ADJUST, zero contradição. A TESE ("adotar com wrapper, nunca cru")
sobreviveu aos três. O que caiu foi o DESENHO: W0 como escrito roda
capacidade Tier-C sem o manifesto que a autoriza, o wrapper está no
mecanismo errado (skill p/ enforcement), e três moldes citados não
alcançam o substrato do /loop.

## Consenso (2+ críticos) — vinculante via §Emendas do plano

- **C1 (A+C, P0): §Cost ausente é BLOQUEADOR pelo próprio ADR-125:230-236.**
  Nenhuma wave que gaste tokens roda antes de o plano ter `## Cost` com
  (a) tokens/tick por perfil (W0-tick vs nightly-tick), (b) cap diário,
  (c) mecanismo de enforcement NOMEADO — + `budget_usd_estimate` e
  `tier_mix_estimate`/`rationale` no frontmatter. A dispensa "Owner
  presente" não existe no ADR (grep zero) — removida.
- **C2 (A+B, P0): 8º gap — composição com a posture de permissão.**
  `night-mode on` grava `acceptEdits`; um tick herdaria ESCRITA sem
  prompt. W2.8 novo: tick-0 lê a posture efetiva e RECUSA fail-closed
  (`acceptEdits`/`bypassPermissions`/`dontAsk`/`auto`; enum derivado da
  autoridade) com controle positivo da recusa; simetricamente,
  `night-mode on` recusa com cron/loop vivo.
- **C3 (A+B): W0 JAMAIS num hold real.** A LINHA DURA é promessa, não
  mecanismo (não há guard p/ `git tag`/`git push` simples; lição S303), e
  a doutrina canônica já atribui vigia ao Monitor (que S311/S312 provou
  superior p/ este caso: processo externo, sem modelo, sem escrita). W0
  reescopado: ensaio em CLONE com tag falsa, objetivo = exercitar
  RECORRÊNCIA/ScheduleWakeup (o que só o /loop tem), $0 de modelo ou
  opt-in Tier-C completo — sem terceira via.
- **C4 (A+B): mecanismo = COMPOSIÇÃO, não skill.** MECHANISM-SELECTION:63
  responde OQ-3 contra o plano; o próprio molde night-mode é
  comando+script+guard+deny (zero skill). W2 vira: comando
  `loop-governed.md` + `scripts/loop_governed.py` (adicionado ao
  `_CANONICAL_GUARDS`) + HOOK novo para budget/teto/proibição (cerimônia
  GPG + ADR — reajustar orçamento de W2). Skill, se existir, só doutrina.
  Guard de `.claude/commands/**` por CLASSE (a instância repete o defeito
  que o F3 do 156 fechou).
- **C5 (A+B+C): os trilhos de budget atuais são CEGOS ao tick.**
  `check_cost_envelope` (matcher Bash + assinatura de coordinator) e
  `check_budget` (matcher Agent) não veem /loop; `is_disabled()` faz
  passthrough sem `CEO_SWARM=1`. Cada gap declara o PONTO DE INTERCEPTAÇÃO
  (evento de hook + o que acontece na recusa); W2.2 nomeia
  `CEO_SWARM`/`class_tier`/`per_plan` + prova de RECUSA (senão é o teatro
  da lição t10).
- **C6 (A+B): medir QUAIS eventos de hook um tick dispara** = AC de W1,
  BLOQUEANTE de W2 (canal presumido nunca provado = classe ADR-153).
- **C7 (A+B): evento novo landa COM consumidor na mesma wave** (precedente
  bom: swarm_iteration; ruim: HMAC de execution_context, 0 produtores).
  W1: sondar o SHAPE de `CronSummary` ANTES do bump de SPEC; logar só
  derivados (contagem, intervalo, sha256 do prompt — NUNCA o corpo).
- **C8 (A+B): kill-switch nunca foi visto funcionando.** Controle positivo
  de `CLAUDE_CODE_DISABLE_CRON` (loop de brinquedo, provar que o tick
  seguinte NÃO dispara, medir latência) é o PRIMEIRO AC do plano — se
  falhar, o veredito vira "não adotar". Kill-file em disco além do env
  (env não atravessa sessões).
- **C9 (B, endossado por A-Unseen): estado inter-tick é superfície de
  injeção PERSISTENTE.** Allowlist de campos estruturados (nunca prosa),
  releitura tratada como untrusted (fenced+capped como retorno
  inter-agente), `CEO_UNICODE_HARDBLOCK=1` durante loop; W2.6 implementada
  em HOOK (a prosa de skill decai 30-59% sob compactação — PLAN-179) e
  ordenada APÓS o Constraint Pinning do 179.
- **C10 (C, endossado por A): tier do tick nomeado = `sonnet`** (Haiku
  proibido sem torneio; herança de Opus é o trap A3). Números no CORPO do
  plano: W0 ≈ $4,6-5,5/piloto (cache sempre frio: 60min > TTL 5min — caso
  ÚNICO, não borda; estoura `vibecoder.per_plan` $3), nightly ≈
  $0,19-0,23/dia perpétuo com dono nomeado (OQ-5: FinOps revisa
  tokens/tick no fechamento de trem; nightly reporta no morning_ledger).

## Single-critic mantidos

- B-Unseen: **fronteira de identidade** — tick roda com credenciais do
  Owner (git/gh/GPG-agent com socket vivo: pode ASSINAR). Gap próprio ou
  exclusão explícita no threat model.
- B: **matriz de composição** loop × night-mode × swarm × Workflow com
  combinações proibidas declaradas.
- B: W2.5 reescrita sobre sinal REAL (o proxy `_OWNER_READ_ACTIONS =
  {session_start}` é auto-fabricável por sessão filha e o detector é
  no-op p/ /loop) — ou declarar NÃO-ENTREGUE.
- A-Unseen: envelope compartilhado (`project+user+date`) sem atribuição
  por loop ⇒ "máx 1 loop governado por projeto" vira invariante com
  enforcement + `loop_id` em todo evento de tick.
- A: modo degradado — falha de INFRA do hook de enforcement no meio de
  loop não-atendido: decidir explicitamente entre fail-open padrão e a
  exceção deliberada ADR-186 (fail-closed com rota de recuperação).
- A-P2-8: referência PLAN-135 é dangling no disco — corrigir a citação
  para a doutrina real (AUTONOMOUS-LOOP-GUIDE §6).
- A: W2.3 precisa de CHAVE DE CLASSE mecânica p/ "mesma classe de achado"
  (senão é julgamento do modelo, que a própria AC-W0.2 proíbe).
- B: checar `CEO_SOTA_DISABLE` no tick-0 e recusar.

## Verdict

**PROCEED** (design-coherent pós-emendas). Como o redesenho de W0/W2 é
substancial, o plano PERMANECE `draft` até o Owner revisar as emendas —
`reviewed` é decisão exclusiva dele. Ship gated por V1/V2/V3 (o hook novo
+ script canonical exigem cerimônia; §Cost é condição de qualquer wave).
