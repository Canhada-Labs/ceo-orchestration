---
id: PLAN-164
title: Pair-rail liveness — timeout uplift + re-âncora do GATE-V2
status: draft
created: 2026-07-29
owner: CEO
depends_on: [PLAN-163]
budget_tokens: 60-120k
budget_sessions: 2
context_risk: low
external_wait: none
tags: [pair-rail, hooks, kernel, incident, gates]
---

# PLAN-164 — Pair-rail liveness: timeout uplift + re-âncora do GATE-V2

## Context

Incidente formal ratificado pelo Owner em S285 (2026-07-29, opção C do
tie-break). Evidência completa em
`.claude/plans/PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md`:

- O default `CEO_PAIR_RAIL_TIMEOUT_S=30` é estruturalmente menor que a
  latência real de um verdito codex in-hook: **36,3 s medidos** com prompt
  realista (gpt-5.6-sol, reasoning xhigh; 8,3 s num round trivial pelo
  MESMO binário pinado ADR-182).
- **12 de 12 `pair_rail_case` na história inteira do audit-log são
  F/TIMEOUT** — o rail nunca completou um review vivo. O pin do PLAN-163
  corrigiu integridade (payload/verify-then-invoke, self-check OK), não
  latência.
- O log é append-only (HMAC): o case-F do probe fresco de 2026-07-29 tornou
  `failopen==0` insatisfazível contra a âncora atual
  (`a4371c7` / 2026-07-29T10:16:16-03:00) — o GATE-V2 do PLAN-163 exige
  RE-ANCORAR além do fix.
- O main-pack staged do PLAN-163 NÃO toca `check_pair_rail.py` (0 hits no
  MANIFEST), mas CONTÉM `settings.json` + `templates/settings/*` com a
  registration em `timeout: 60` — o fix de kernel exige sincronizar o pack
  congelado (senão a cerimônia do pack REVERTE o timeout), com re-review
  delta dos bytes mudados.

Colateral fora de escopo: `stop_review` nudge-only transiente (S284).

## Goal

O rail completa reviews vivos com margem honesta (healthy cases A-E
observáveis), o GATE-V2 do PLAN-163 é re-ancorado e passa, e a cerimônia do
main-pack fica desbloqueada.

## Approach

Uma cerimônia única (Owner, GPG, `CEO_KERNEL_OVERRIDE`) sobe o budget
interno do hook E o teto da registration no harness, com paridade de
templates e sync do pack congelado; a própria cerimônia re-ancora o
GATE-PIN-ANCHOR; prova fresca em sessão nova fecha o gate. Alternativa
rejeitada: env-knob por sessão (opção B do tie-break) — não corrige o
default da frota (adopters seguem 100 % fail-open) e a prova não valeria
para a configuração shipada.

Classificação: **L3+** (security rail + kernel settings.json) → debate
obrigatório antes da execução (`/debate start PLAN-164`), ADR para a
mudança de contrato de timeout do rail (amend do ADR-106/110 ou ADR novo —
decidir no debate).

## Waves

### W0 — Ratificação de parâmetros (Owner tie-break)
Check: none (doc-only)
- [ ] OQ1-OQ4 respondidas; literais materializados nos ACs de W1 antes do
  staging.

### W1 — Staging + testes (nada toca a árvore canônica viva)
- [ ] Staged `check_pair_rail.py`: default `"30"` → literal OQ1 no
  `os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", ...)` (~L1717), fallback
  `timeout_s = 30.0` (~L1720/1722) e docstring (~L51-52); clamp `>600`
  mantido. Check: `python3 -m pytest .claude/hooks/tests/ -k pair_rail -q`
  verde no overlay de staging.
- [ ] Staged kernel `settings.json`: registration do `check_pair_rail.py`
  `timeout: 60` → literal OQ2 + `_comment` "(default 30s)" atualizado.
  Check: oracle hook-stdout-schema + settings-parity verdes no overlay.
- [ ] Paridade de template: `templates/settings/settings.base.json`
  (registration ~L97) mesmo timeout OQ2. Check: diff mecânico das duas
  registrations idêntico (mesmo valor), suíte de parity verde.
- [ ] Sweep de testes que assertam o default antigo (30/60): atualizar
  espelhos + adicionar teste explícito do valor default novo.
  Check: `grep -rn "TIMEOUT_S" .claude/hooks/tests/` não retorna
  asserções do valor antigo; suíte cheia verde.
- [ ] Sync do pack congelado PLAN-163: aplicar o MESMO delta de timeout em
  `staged/main-pack/.claude/settings.json` +
  `staged/main-pack/templates/settings/settings.base.json`; recomputar
  `MANIFEST.sha256` + gêmeo tracked `inputs-pack.sha256` (+commit);
  re-review DELTA registrado em `PLAN-163/review/` (profundidade OQ4).
  Check: `shasum -c` dos manifests PASS; arquivo de review delta
  commitado.

### W2 — Cerimônia (Owner-run via `!`, GPG)
- [ ] Sentinel round novo (escopo exato = arquivos do W1 vivos); apply sob
  `CEO_KERNEL_OVERRIDE`; commit assinado `[SENT-PLAN164-RAIL]`.
  Check: `touched − scope = ∅`; suíte pós-apply verde.
- [ ] Re-âncora (OQ3): atualizar `.claude/plans/PLAN-163/GATE-PIN-ANCHOR`
  para sha+ts do commit `[SENT-PLAN164-RAIL]`, declarado no Scope do
  sentinel. Check: `land-plan163-pin.sh --gate-v2` imprime a âncora nova.
- [ ] Closeout: claims + verify-counts + push + Validate.
  Check: `gh run watch` do Validate = success.

### W3 — Prova fresca + desbloqueio do PLAN-163
- [ ] Sessão NOVA (a registration nova só vale pós-restart do harness);
  probe bytes-idênticos (padrão S281) → case A-E esperado.
  Check: `land-plan163-pin.sh --gate-v2` = PASS (expected≥1 ∧ healthy≥1 ∧
  failopen==0 ∧ unclassified==0 ∧ deficit==0 pós-âncora-nova).
- [ ] Registrar o PASS em `PLAN-163/probes/`. Check: arquivo commitado.
- [ ] Handoff: PLAN-163 Passo 4 (cerimônia do pack) liberado com
  `--confirm-gate-pin-done --confirm-gate-v2-fresh` verdadeiras.
  Check: none (executa no PLAN-163).

## Open questions

- **OQ1 — default interno novo.** Draft: **100** (36,3 s medido + margem
  para diffs maiores e carga de runner; clamp 600 mantido). Alternativa
  minimal-change: 48 (cabe no teto atual de 60 s sem mexer no kernel, mas
  margem de ~12 s é a mesma classe de aposta que produziu o 30).
- **OQ2 — registration do harness.** Draft: **120** (interno 100 +
  overhead ~10-15 s de startup/redaction/validação). Custo de UX a debater:
  um edit canônico NÃO-sentinelado passa a segurar o PreToolUse por até
  ~100 s antes do verdito/fail-open (hoje o teto era 30 s).
- **OQ3 — mecânica da re-âncora.** Draft: atualizar `GATE-PIN-ANCHOR` no
  commit da própria cerimônia PLAN-164 (transparente, assinado, declarado
  no Scope). Alternativa: re-rodar `land-plan163-pin.sh` (risco de morrer
  em commit vazio — sem handling no script).
- **OQ4 — profundidade do re-review do pack pós-sync.** Draft:
  delta-confirm de 1 round (codex + grok) escopado aos bytes mudados
  (timeout da registration), não um ciclo full de 6 rounds.

## How to continue

Sessão nova: Gate 1-3; ler este plano + o diagnóstico em
`PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md`. Se `status: draft`:
rodar `/debate start PLAN-164` (L3+), resolver OQ1-OQ4 com o Owner,
`draft → reviewed`. Se `reviewed`: executar W1 (staging), depois cerimônia
W2 via `!` e prova W3 em sessão nova.

## Success criteria

- [ ] GATE-V2 do PLAN-163 = PASS registrado sob a âncora nova.
- [ ] Rail com pelo menos 1 case healthy (A-E) real no audit-log — o
  primeiro da história do log.
- [ ] Paridade dogfood ↔ template mantida; pack congelado sincronizado com
  manifests self-consistentes e re-review delta registrado.
- [ ] Suíte + Validate verdes; claims/verify-counts sem drift.
- [ ] Nota honesta: o row 168h do ceo-boot segue RED até os 12 case-F
  antigos saírem da janela (~2026-08-05) — esperado, registrar e ignorar
  (mesma nota do runbook do PLAN-163).

## Owners / Blockers / Next

- **Owner:** CEO (execução) + Owner humano (tie-breaks OQ1-OQ4, GPG W2).
- **Blocker atual:** debate L3+ pendente + OQ1-OQ4 sem ratificação.
- **Next:** `/debate start PLAN-164 "timeout uplift do pair-rail (interno
  100 / registration 120) + re-âncora GATE-V2 via cerimônia única"`.
