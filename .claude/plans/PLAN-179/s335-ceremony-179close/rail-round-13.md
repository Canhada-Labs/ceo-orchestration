# wave-179close — rail codex rodada 13 (sombra pós-curas r12, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (2 P2 — ambos verificados REAIS; curados ANTES da r14)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r13.txt` (9.177
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.
Refutados anteriores não voltaram (4ª rodada seguida).

## Os achados (verificação + cura)

1. **[P2] Rollback PARCIAL fabricava `absent`** — VERIFICADO (refina a
   r11): relógio restaurado para TRÁS mas ainda DEPOIS do start (start
   10:00, escrita 11:00, restore 10:30) — o mtime fica acima do teto, o
   check de inversão da r12 não dispara, e um arquivo genuinamente
   escrito na sessão pré-rollback sumia num `absent`. CURA: mtime de
   arquivo regular acima do teto é ANOMALIA (`skewed_seen`): bloqueia
   toda classe-ausência (⇒ `error`) e a exclusividade do `index_only`
   (⇒ `written`), na mesma álgebra do `scan_incomplete`. Controle:
   `test_future_mtime_is_outside_the_window` reescrito (o assert `absent`
   da r11 virou `error` — atualização CONSCIENTE registrada aqui).
2. **[P2] O except do emitter era silencioso** — VERIFICADO: `_lib.
   audit_emit` corrompido/raise em upgrade parcial sumia com a evidência
   assinada do US8 sem rastro, contra a regra fail-open-com-breadcrumb.
   CURA: stderr breadcrumb com o TIPO da exceção (repr poderia carregar
   internals do emitter), embrulhado em try próprio. Controle:
   `test_emitter_infra_failure_leaves_breadcrumb` (emitter raising via
   patch no módulo — o lookup é vivo, classe audit_emit-stale da S328).

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **331/0** (7.29s) —
`EXPECTED_UNIT_PYTEST_PASSED` 330→331 (+1 controle novo; 1 reescrito com
assert mais forte). Curas confinadas a 2 paths do EXPECTED. Refinalize +
r14 na sequência.
