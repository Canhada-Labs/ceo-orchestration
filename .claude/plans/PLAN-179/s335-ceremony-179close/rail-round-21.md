# wave-179close — rail codex rodada 21 (sombra pós-curas r20, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (1 P1 + 2 P2 — TODOS verificados REAIS; curados ANTES da r22)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r21.txt` (10.570
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.

## Os achados (verificação + cura)

1. **[P1] `ignorepreviousrules.md` (run 19) passava o cap de 24** —
   VERIFICADO. O cap desceu para **14 = corpus medido + 1**: sonda r21
   varreu TODOS os nomes reais do diretório de memória — maior token =
   13 (`authorization`). Ratchet DECLARADO como de corpus, não prova
   semântica: uma diretiva ≤14 chars concatenada segue expressável, mas
   com pouco poder instrutivo dentro do frame de lista de arquivos, e o
   validador vê qualquer forma tokenizável (expansão r19/r20).
   Controle: asserts atualizados no teste do charset.
2. **[P2] O branch de plan-FILE divergia do derive_scope canônico** —
   VERIFICADO: o canônico só aceita plan_dir + AC-declarado; o 3º shape
   (que a r7 apenas apertara) fazia empate `PLAN-010-x.md` vs
   `PLAN-020/n.md` eleger planos DIFERENTES nos dois derivadores para o
   MESMO commit ⇒ PostCompact reinjetaria o ledger errado. CURA: branch
   REMOVIDO — fidelidade de espelho é o contrato; o arquivo de plano cai
   em unmatched e segue a MESMA perna AC. Teste re-escrito
   (`test_plan_file_shape_does_not_match_directly`); os negativos da r7
   seguem valendo (tudo não-plan_dir é None).
3. **[P2] Timeouts fixos downstream estouravam o TIME_BUDGET_S** —
   VERIFICADO: pós-índice (fatia 1.0s), `_last_tag_time` tinha 2.0s
   fixos e o lock do hmac-breadcrumb +0.5s ⇒ ~3.5s > 2.5s. CURA: o
   deadline compartilhado atravessa `_last_tag_time(timeout_s=resto)` (o
   floor do `_git` da r8 lida com resto ≤0.05 ⇒ "") e o lock-wait vira
   `min(0.5, resto)` com leitura lockless quando o resto acabou
   (advisory sidecar, corrida de um evento inofensiva — doutrina já
   declarada no próprio docstring).

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **347/0** (7.65s) —
contagem inalterada (asserts em testes existentes + 1 teste re-escrito,
declarado). Curas confinadas a 3 paths do EXPECTED. Refinalize + r22 na
sequência.
