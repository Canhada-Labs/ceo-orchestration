---
id: PLAN-171-FOLLOWUP-readinjection-docstring
parent: PLAN-171
title: Texto canônico desatualizado do PLAN-171 — docstring do check_read_injection e teto G12 da skill de paralelização
status: draft
created: 2026-10-10
owner: CEO
depends_on: [PLAN-171]
tags: [docs, canonical, followup]
---

## Context

O PLAN-171 fechou na W0 em 2026-10-10. Duas frases canônicas ficaram
desatualizadas e só saem por cerimônia GPG (oráculo `--is-canonical` = 1 nos
dois arquivos, conferido em 2026-10-10).

1. **Docstring do `check_read_injection.py`.** A linha 4 diz «Optional,
   advisory. Always allows the read.» O lote 2 da W0 mediu que o hook BLOQUEIA
   sob `CEO_UNICODE_HARDBLOCK=1` (`PLAN-171/w0/lote-2-S347.md`, Apêndice F;
   registro do pai, entrada `p171-w0-lote2-fix`). A própria docstring já diz
   «Always allows UNLESS `CEO_UNICODE_HARDBLOCK=1`» na linha 32. A cura é
   qualificar a linha 4 do mesmo jeito.
2. **Teto G12 na skill de paralelização** (metade canônica da W1d do pai).
   `.claude/skills/core/parallelization-by-default/SKILL.md:93-95` ainda diz
   «max 6 parallel sub-agents» e «Hard cap: N <= 6». O pai registra que o teto
   ratificado é 8 read-only (§5) e que a medição PLAN-083 P0-1 deve ser relida
   antes de mudar o número (registro do pai, entrada de 2026-09-07).

As duas peças ficam juntas porque são do mesmo tipo: texto canônico que
contradiz o comportamento medido. O slug do arquivo nomeia só a primeira.

## Goal

Nenhuma das duas frases contradiz o comportamento medido.

## Items

### W1 — docstring  [P2]  (canônico)
- Qualificar a linha 4. Pode ir de carona no pacote canônico do
  `cost_envelope_capped` (`PLAN-171-FOLLOWUP-cost-envelope-emit`), se esse
  pacote ainda estiver aberto.

### W2 — teto G12  [P2]  (canônico; `SKILL.md` exige rota SP-NNN)
- Reler a medição PLAN-083 P0-1, medir de novo no Claude Code vigente e só
  então trocar o número.

## Open questions

- **OQ-1.** Qual número entra na skill? O pai fala em 8 read-only (G12). O
  PLAN-194 registra outro teto operacional, 8 agentes vivos e 12 só depois da
  W2.6 (decisão D-21, `PLAN-194-maintenance-train-v1-4-3.md:2093`), e o
  `PLAN-194/LEDGER.md:99` diz que essa regra ficou sem gatilho quando a W2.6
  foi para a 1.4.4. A decisão é do Owner, com a medição nova na mão.

## Success criteria

- [ ] A linha 4 do `check_read_injection.py` deixa de afirmar «Always allows» sem qualificação.
  Check: `sed -n 4p .claude/hooks/check_read_injection.py`
- [ ] A skill de paralelização traz o teto decidido na OQ-1, com a medição citada.
  Check: `grep -n 'Hard cap' .claude/skills/core/parallelization-by-default/SKILL.md`
