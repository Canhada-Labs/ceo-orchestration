# DESIGN — wave-183batch (S335, 2026-08-31)

**Ratificação (Owner, AskUserQuestion na S334, verbatim no runbook
`PLAN-179/NEXT-S335-RUNBOOK.md` §2):** PLAN-183 = «Batch menor + começar
W1» — batch canônico completo com rail; W1 avança sem promessa.

## Decisões de desenho

1. **O settings shipado é o DERIVADO, nunca um snapshot.** Prova em três
   pernas: idempotência (re-gerar+re-aplicar = sha idêntico, finalize 4a e
   LAND V3a), NÃO-vacuidade (cópia descartável sem `prisma-patterns` →
   o fragment a recupera, 4e/V3b — um fragment inerte seria idempotente
   por vacuidade), e o gate REAL (`check_harness_config.py` rc 0 sobre o
   pós-patch, 4g/V4, custa <1s).
2. **Delta medido antes de fixar**: `jq -f` do fragment sobre o vivo =
   **+4 adds, zero remoções, zero mudanças de valor** (cpp-testing,
   frontend-slides, prisma-patterns, ui-demo — 0-dispatch na janela). As
   duas entradas fintech do runbook (`:884-885`) permanecem por mérito
   (domain-tier 0-dispatch).
3. **INERT header = comentário puro no molde do benchmarks** — o
   frozen-subset (11 steps + pins) não muda um byte de contrato;
   `test_validate_template_frozen_subset.py` 7/7 é a régua.
4. **AC-5 por REGISTRO com evidência nomeada** (yml:485 → sh:180). A nota
   ◐ da S334 descrevia o estado pré-`738007e`; medição contra o DISCO
   supersede prosa. AC-2/OQ-2 (execução real do workflow ativado) fica
   explicitamente fora — decisão do Owner.
5. **KERNEL**: settings.json ∈ `_KERNEL_PATHS`; LAND arma o override no
   menor escopo (molde adrgate/cfab980, contrato reason-SLUG+I-ACCEPT
   validado vivo — T20e do harness).
6. **W3-P1 (de-embed) FORA** por regra do runbook (coordenação com a
   `_derivation` da wave-F não é óbvia em 30 min ⇒ follow-up).

## Mold-finding (paga pela família)

O T0 dos harnesses herdados usava `grep -ohE '_expect [A-Z_]+'` — corta
chaves com DÍGITO (`EXPECTED_AC5_CHECKED` → `EXPECTED_AC`) e dá falso
vermelho na bijeção. Curado aqui E retrofit no harness do 179close;
latente nos molds anteriores (nenhuma chave tinha dígito até hoje).

## Números medidos (fontes no EXPECTED-BASELINE.txt)

- overrides 104 → 108; frozen-subset 7/0; INERT/COMMENT/AC5 = 1 cada;
  canonical=1 (oráculo), manifest=0, PY=0 no patch (3 paths).
