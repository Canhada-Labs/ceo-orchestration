---
plan: PLAN-164
round: 1
created_at: 2026-07-29
proposal: "timeout uplift do pair-rail (interno 100 / registration 120) + re-âncora GATE-V2 via cerimônia única"
---

# PLAN-164 — proposta para debate round 1

Plano completo: `.claude/plans/PLAN-164-pair-rail-timeout-uplift.md`.
Evidência do incidente: `.claude/plans/PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md`.

## Tese

O pair-rail (V2 do verification cascade — o ÚNICO truth gate LLM) nunca
completou um review vivo in-hook: **12 de 12** `pair_rail_case` na história
inteira do audit-log são F/TIMEOUT. Root cause MEDIDO em 2026-07-29:

- Round codex trivial pelo binário pinado (ADR-182): **8,3 s** (rc=0).
- Round realista de review (~2 KB, shape `build_verdict_argv`,
  gpt-5.6-sol, reasoning xhigh): **36,3 s** (rc=0, verdito PASS).
- Default do hook: `CEO_PAIR_RAIL_TIMEOUT_S=30` → TIMEOUT → fail-OPEN
  (case F) em 100 % das invocações reais.

O fix proposto: subir o budget interno default 30→100 s e o teto da
registration no harness (settings.json, kernel) 60→120 s, com paridade de
templates, numa ÚNICA cerimônia GPG que também re-ancora o GATE-V2 do
PLAN-163 (o log append-only tornou `failopen==0` insatisfazível contra a
âncora atual `a4371c7`).

## Escopo (superfícies tocadas)

1. `.claude/hooks/check_pair_rail.py` — default literal 30→100 (env-get
   ~L1717, fallback ~L1720/1722, docstring ~L51-52); clamp `>600` mantido.
2. `.claude/settings.json` (KERNEL) — registration `timeout: 60→120` +
   `_comment`.
3. `templates/settings/settings.base.json` — mesma registration (~L97),
   paridade dogfood↔template.
4. Testes: sweep de asserções do default antigo + teste explícito do novo.
5. Sync do pack CONGELADO do PLAN-163 (`staged/main-pack/` contém
   settings.json + settings.base.json com timeout 60): mesmo delta +
   recompute MANIFEST.sha256 + gêmeo `inputs-pack.sha256` + re-review
   DELTA (senão a cerimônia do pack REVERTE o fix de kernel).
6. Re-âncora: `.claude/plans/PLAN-163/GATE-PIN-ANCHOR` → sha+ts do commit
   `[SENT-PLAN164-RAIL]`, declarado no Scope do sentinel.
7. ADR: amend do ADR-106/110 (contrato de timeout do rail) ou ADR novo —
   decidir neste debate.

## Decisões já tomadas (contexto, não re-litigar)

- Opção C ratificada pelo Owner (tie-break S285): incidente formal,
  pack do PLAN-163 ADIADO até este fix. Alternativas A (fix 30→48 sem
  kernel) e B (env-knob por sessão) foram rejeitadas pelo Owner.
- O pin ADR-182 (verify-then-invoke) está saudável — self-check OK e o
  MESMO binário completa rounds manualmente. NÃO é escopo re-abrir o pin.
- Fail-open em timeout é o contrato do rail (ADR-106) — NÃO é escopo
  mudar para fail-closed aqui.

## Open questions para o debate (drafts do CEO)

- **OQ1 — valor do default interno.** Draft: **100 s** (36,3 s medido +
  margem para diffs maiores e carga). Alternativa: 90/120. Piso honesto:
  ≥60 s (2× o medido é apostar de novo na mesma classe do 30).
- **OQ2 — registration do harness.** Draft: **120 s** (interno + overhead
  ~10-15 s). CUSTO DE UX: um edit canônico não-sentinelado segura o
  PreToolUse por até ~interno s antes do verdito/fail-open (hoje teto 30 s
  efetivo). O debate deve pesar: latência de sessão × primeiro healthy
  case da história do rail.
- **OQ3 — mecânica da re-âncora.** Draft: atualizar GATE-PIN-ANCHOR no
  commit da própria cerimônia (transparente, assinado, Scope declarado).
  Alternativa: re-rodar `land-plan163-pin.sh` (risco commit-vazio).
- **OQ4 — profundidade do re-review do pack.** Draft: delta-confirm
  1 round (codex+grok) escopado ao delta de timeout. Alternativa: full
  re-review (custo alto, delta minúsculo).

## Riscos conhecidos (para os críticos atacarem)

- 100 s de PreToolUse síncrono: sessões podem parecer travadas durante um
  review vivo; nenhum feedback intermediário ao operador.
- O harness mata o hook aos `timeout` da registration — se interno ≥
  registration−overhead, o TIMEOUT vira hook-kill (unclassified? deficit?
  qual é o comportamento observável do gate nesse caso?).
- Sync do pack congelado reabre superfície de review (bytes mudam pós
  double-APPROVE) — delta-review precisa ser suficiente e auditável.
- Re-âncora editada por cerimônia: é a MESMA classe de "mexer no arquivo
  do gate" que seria tamper se feita fora de cerimônia — o Scope do
  sentinel precisa deixar isso inequívoco.
- Latência codex é variável exógena (carga da API, effort xhigh
  configurado fora do repo): 100 s é aposta calibrada, não garantia.

## Formato exigido da crítica (DEBATE-SCHEMA §4)

Verdict (ACCEPT/ADJUST/REJECT), Summary, Risks, Must-fix, Nice-to-have,
Unseen, What I would NOT change.
