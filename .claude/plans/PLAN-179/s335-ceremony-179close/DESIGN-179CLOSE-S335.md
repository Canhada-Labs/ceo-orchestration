# DESIGN — wave-179close (S335, 2026-08-31)

**Ratificação (Owner, AskUserQuestion no fim da S334, verbatim no runbook
`PLAN-179/NEXT-S335-RUNBOOK.md`):** (1) «Fechar tudo» — pack US7+US8, AC(a)
do W0 supersedido pela r1-C3, válvula US2b resolvida, flip `done` no patch;
(2) válvula = «Eta advisory + doutrina».

## Decisões de desenho (as que o rail vai querer interrogar)

1. **US7 sem tocar o SPEC.** O `ledger_index` vive DENTRO do blob do
   snapshot (scratchpad), nunca no wire: `compaction_continuity_snapshot` e
   `compaction_context_reinjected` mantêm os field-sets existentes e
   `pointer_count` mantém a semântica (um pointer a mais dentro do clamp
   0..9 não é re-scope). Títulos de seção ficam FORA do instruction stream
   (R5 P1-1) — o pointer é path + short-sha.
2. **US7 deriva por PATHS, com espelho LITERAL.** O contrato de hooks
   proíbe import hook-a-hook, então o tie-break de
   `check_ledger_checkpoint.derive_scope` (mais paths ganha; empate → menor
   id) é espelhado, não importado. Teste AST escopado às DUAS funções novas
   — o hook legitimamente usa `_resolve_plan_id` para o ESCOPO DE ESCRITA
   do snapshot; o ban da r1-C6 é sobre a derivação do índice.
3. **US8 implementado DA spec assinada** (`staged-w24/SESSIONEND-NOTE.md`),
   com UM desvio mínimo documentado: `_session_start_ts` devolve
   `(ts, anchor_source)` porque o §4 põe `anchor_source` no wire e nenhuma
   assinatura §3 o produz. Alternativa rejeitada: globals/módulo-estado.
4. **Valve sem wire.** η vai em stderr (permille inteiro) — o precedente é
   a própria linha v2.56 do SPEC: contagens cruas moram no canal do
   operador. Nada de float; nada de campo novo em evento existente.
5. **Kernel.** `audit_emit.py` ∈ `_KERNEL_PATHS` (o runbook errou nessa
   metade) ⇒ o LAND arma o override no menor escopo, molde adrgate/cfab980.
6. **Pins 330→331 rebaselineados CONSCIENTEMENTE** em 5 suítes + o contrato
   de API (SHA re-derivado do módulo, símbolo público adicionado) — a
   alternativa (relaxar) é proibida pela regra da S328.

## Números medidos (fontes no EXPECTED-BASELINE.txt)

- 304 passed / 0 skipped nas 9 suítes declaradas; 7775 passed / 1 flake
  de perf sob carga (`test_case_a_p99_under_5ms`, verde isolado) na
  bateria completa pós-curas (as 6 falhas originais eram TODAS pins 330;
  o 6º — `test_git_bypass_guard` — só apareceu na captura integral).
- `_KNOWN_ACTIONS` 330→331; golden `# count: 331`; registry checker
  `OK: audit registry in sync`.
- η = 887‰ derivado de F+S=112638 / T=998043 (medidos, w0-measurement §C/§E).
- verify-counts rc 0 na sombra (a margem ±5% absorveu +25 testes).

## O que fica FORA (deliberado)

- Veredito vivo do canal PostCompact (US1): supersedido pela r1-C3 — a
  sonda segue executável como medição opcional.
- CLAUDE.md §5 (linha do ADR-153): atualiza no CLOSEOUT, não neste patch
  (cache-stable; regra do próprio CLAUDE.md §0).
- FU-ADR-README-SEED / FU-ADR-GRAMMAR / staged-w24 remanescentes: decisões
  do Owner já enfileiradas em outro material.
