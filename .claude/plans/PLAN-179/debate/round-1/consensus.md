---
plan: PLAN-179
round: 1
round_verdict: PROCEED
verdicts: [Critic-A: ADJUST, Critic-B: ADJUST, Critic-C: ADJUST]
consensus_adjustments: 9
created_at: 2026-08-17T23:40:00-03:00
note: "PROCEED = design-coherent APÓS emendas aplicadas (§8 do plano). NÃO autoriza ship — cascata V0-V3 intocada; reviewed = SÓ o Owner."
---

# PLAN-179 — Consenso round 1

Três críticos, três ADJUST, zero REJECT, zero contradição entre críticos.
O diagnóstico (E1-E4) foi verificado independentemente pelos três contra o
disco e SOBREVIVEU. Os ajustes atacam o DESENHO de W0-W2, não a tese.

## Consenso (2+ críticos) — TODOS aplicados como emendas §8 do plano

- **C1 (A+B): escopo-sessão sem sobrecarregar `plan_id` nem tocar env.**
  Namespace próprio (`store_name` distinto + `scope_kind` no blob; forma
  `session-<uuid>` validada); `session_id` SOMENTE do hook input; se o valor
  derivar de `CLAUDE_SESSION_ID` (env), recusar o fallback. Preserva o
  invariante plan-isolation do store e a proibição M2.
- **C2 (A+B): acúmulo órfão é REAL e ilimitado** (set sem ttl_seconds;
  prune só apaga linhas; $HOME fora do repo). TTL explícito + GC de ARQUIVO
  + teto, dimensionados pelo N/semana medido em W0.
- **C3 (A+B+C): canal.** O pinning nasce em `SessionStart(matcher=compact)`
  (precedente POSITIVO local: turbo_sessionstart + matcher "" wired);
  PostCompact vira reforço. Sonda W0 carrega DOIS canários numa única
  compactação paga. A troca de canal carrega decisão de sanitização
  (payload estruturado/marcador, nunca texto livre).
- **C4 (A+B+C): `context_pressure_observed`** = int com unidade no nome,
  edge-triggered (só transição de bucket), branch `_scrub_` dedicada +
  allowlist + par de testes not-in-passthrough/registered + bump SPEC.
- **C5 (B, endossado por A via R4): conjunto fixado vira CÓDIGO** em
  `_lib/` (já canonical-guarded); o `.md` é doc DERIVADA com teste
  `set(md)==set(código)`. Mudança do conjunto = cerimônia. Resolve a
  autocontradição de US5b ("não derivado de disco" vs conjunto em .md).
- **C6 (A+C): gatilho do ledger deriva dos PATHS do commit**
  (`.claude/plans/PLAN-NNN/**` ou path de AC), NUNCA de `resolve_plan_id`
  — senão W2 re-herda a causa-raiz do E2. Skip fora de escopo = evento
  nomeado com enum (omissão visível).
- **C7 (C, endossado por A): paths de teste reais.** US5/US5d citam
  arquivos inexistentes; o real é `test_check_compaction_continuity.py`
  (com dual-loader `_pick()` + `_AuditEmitSlotGuard`). O teste
  `test_no_plan_transition_degrades_to_unavailable:273-281` AFIRMA o bug —
  editá-lo é AC explícita de US3/US5 (nunca apagar: vira asserção do NOVO
  comportamento). US5d reescrita como propriedade ARQUITETURAL (o payload
  pinned NUNCA participa do bloco enviado ao sumarizador), não como
  afirmação sobre o comportamento do modelo.
- **C8 (A+B): governança completa.** §7 enumera o escopo REAL do sentinel
  (hooks tocados + settings.json + SPEC, não só 2 ADRs); números de ADR
  alocados no momento da escrita (191/192 já tomados); DOIS ADRs, UMA
  cerimônia, AMEND-1 primeiro.
- **C9 (B, endossado por C via medição): claim "secrets-redacted" é FALSA**
  no caminho usado (payload bytes pula redact_secrets que só cobre str).
  Corrigir redação + SPEC/v1/audit-log.schema.md:516 + docstrings na MESMA
  cerimônia.

## Achados single-critic MANTIDOS (entram nas emendas)

- A-U1: critério de MORTE do ledger na janela measure-first (taxa de
  omissão > X% ⇒ REMOVER, não manter como dívida).
- A-U2: ADR-193 nasce com matriz de 2+ opções (incl. ledger DERIVADO do
  audit-log — elimina escrita discricionária) — exigência da skill.
- A-U3: teto de tamanho do LEDGER.md (conflito W2×W3 no orçamento F).
- A-U4: fronteira = momento de MÁXIMA pressão; "ACs com estado verificado"
  ganha VERIFICADOR nomeado (comando/exit code), porque entrada errada é
  pior que ausente.
- B-M4/M5: write-gate fail-CLOSED (distinguir "limpo" de "não escaneável";
  o segundo = hit) + descarte VISÍVEL escopado por proveniência
  (owner/ceo-derived nunca passam pelo scanner; FPR medida em janela
  advisory — o catálogo atual sobre-dispara em texto legítimo).
- B-Unseen: ledger no repo PÚBLICO ⇒ regra "identificadores verbatim,
  nunca corpo" + check-contamination cobrindo o path.
- C-R5: sonda W0 é operator/local-only (nunca CI) + idempotência declarada.
- C-R6: metade de F (system prompt + tool defs) não é mensurável por
  context-budget.py — fonte nomeada (usage da API) ou a AC degrada para
  estimativa declarada.

## Rejeitados / adiados

- Nenhum achado foi rejeitado. B-Nice (tirar pinning de trás de
  CEO_COMPACTION_CONTINUITY=0) adiado para decisão em W1-b (registrado).

## Verdict

**PROCEED** (design-coherent) condicionado às emendas §8 já aplicadas no
plano. Shipping continua gated pela cascata: V1 testes, V2 pair-rail Codex
em W1/W2/W4, V3 cerimônia GPG (AMEND-1 + ADR novo), e `reviewed` é decisão
exclusiva do Owner.
