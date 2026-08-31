# DESIGN — wave-183batch (S335, 2026-08-31)

**Ratificação (Owner, AskUserQuestion na S334, verbatim no runbook
`PLAN-179/NEXT-S335-RUNBOOK.md` §2):** PLAN-183 = «Batch menor + começar
W1» — batch canônico completo com rail; W1 avança sem promessa.

## Decisões de desenho

1. **O settings shipado é o DERIVADO, nunca um snapshot.** O gerador é
   INCREMENTAL (medido no redesenho pós-abort do 4e: sobre a árvore já
   atualizada emite 0 chaves — «re-gerar e comparar» seria prova vácua),
   então o fragment EXATO da mudança virou MATERIAL VERSIONADO
   (`skill-frag-s335.jq`) e a prova é: `base + fragment` ⇒ settings do
   patch BYTE A BYTE (4a/V3a), com não-vácuo NOMEADO na mesma passada
   (`prisma-patterns` ABSENT→name-only, 4e/V3b) e o gate REAL
   (`check_harness_config.py` rc 0, 4g/V4).
2. **Delta medido antes de fixar**: `jq -f` do fragment sobre o vivo =
   **+4 adds, zero remoções, zero mudanças de valor** (cpp-testing,
   frontend-slides, prisma-patterns, ui-demo — 0-dispatch na janela). As
   duas entradas fintech do runbook (`:884-885`) permanecem por mérito
   (domain-tier 0-dispatch).
3. **INERT header = comentário puro no molde do benchmarks** — o
   frozen-subset (11 steps + pins) não muda um byte de contrato;
   `test_validate_template_frozen_subset.py` 7/7 é a régua.
4. **AC-5: registro SEM flip** (rail 183-r1 barrou o `[x]`, corretamente —
   o texto do AC exige EXECUTAR o CI entregue e isso é W0-US3/OQ-2). O que
   viaja é o REGISTRO com evidência (yml:485 → sh:180); a nota ◐ da S334
   descrevia o estado pré-`738007e`. O runbook previa as duas saídas
   («se sim… se não») — a medição respondeu NÃO.
5. **KERNEL**: settings.json ∈ `_KERNEL_PATHS`; LAND arma o override no
   menor escopo (molde adrgate/cfab980, contrato reason-SLUG+I-ACCEPT
   validado vivo — T20e do harness).
6. **W3-P1 (de-embed) FORA** por regra do runbook (coordenação com a
   `_derivation` da wave-F não é óbvia em 30 min ⇒ follow-up).

## Mold-findings (pagos pela família)

**`git mv` no header de ativação falha em install fresco** (template
nasce untracked) — curado aqui com `mv`; o MESMO defeito está latente em
`benchmarks.yml.template:5-7` (fora do patch; cura futura).


O T0 dos harnesses herdados usava `grep -ohE '_expect [A-Z_]+'` — corta
chaves com DÍGITO (`EXPECTED_AC5_CHECKED` → `EXPECTED_AC`) e dá falso
vermelho na bijeção. Curado aqui E retrofit no harness do 179close;
latente nos molds anteriores (nenhuma chave tinha dígito até hoje).

7. **A4 de verdade (rail 183-r4).** O runbook mandava «regen do
   skillOverrides» com o A4 vivo; a leitura correta — apontada pelo rail
   e confirmada pelo teste pré-escrito (`test_veto_skill_map` com
   @expectedFailure + companheiro que manda deletá-lo «quando a
   cerimônia landar») — é que as 7 chaves VETO-bearing name-only SÃO o
   defeito. Como o gerador não remove chaves, o undemote é o SEGUNDO
   material versionado (`veto-undemote-s335.jq`), aplicado aos DOIS
   alvos; a lista das 7 veio da AUTORIDADE (bound ∩ overrides, medida).

## Números medidos (fontes no EXPECTED-BASELINE.txt)

- overrides 104 → 108; frozen-subset 7/0; INERT/COMMENT/AC5 = 1 cada;
  canonical=1 (oráculo), manifest=0, PY=0 no patch (3 paths).
