# wave-179close — rail codex rodada 14 (sombra pós-curas r13, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (2 P2 — ambos verificados REAIS; curados ANTES da r15; o 2º REMOVE um artefato do patch: 18→17 paths)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r14.txt` (11.582
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.

## Os achados (verificação + cura)

1. **[P2] Escopo PARCIAL elegia plano** — VERIFICADO: cap estourado ou
   deadline no meio do matching deixava contagens truncadas alimentarem o
   tie-break — um plano com mais paths em escopo podia perder para um
   match direto precoce ⇒ pointer para o LEDGER ERRADO (pior que nenhum,
   doutrina r11-F3). CURA: flag `truncated` em TODAS as pernas de corte
   (slice do git >2000; unmatched >500; deadline pré-fase, por-path e
   pós-fase — a última cobre o mirror parando NO deadline) ⇒ `{}`.
   Controle: `test_truncated_scope_refuses_to_elect_a_plan` (commit de
   501 paths + 1 path de plano: pré-cura derivava PLAN-042, pós-cura
   recusa).
2. **[P2] O waiver global de substring do noop-allowlist era bypass** —
   VERIFICADO e ACEITO na forma FORTE: a entrada era INERTE para o
   propósito declarado (o comando registrado é `python3 …/SessionEnd.py`,
   que a heurística constant-emitter — `prog in {echo,printf,true,:}` —
   nunca flagra; o comentário do próprio arquivo admitia a inércia) e um
   comando SUBSTITUÍDO por `printf 'SessionEnd.py disabled'` passaria
   CALADO pelo waiver de substring, contra o fail-loud do ADR-158 §2.
   CURA estrutural: `harness-noop-allowlist.txt` REMOVIDO do patch
   (nasceu nesta wave; 18→17 paths). Cascata executada no MESMO ciclo:
   SPEC row e docstring corrigem o modelo (o estado `off` não precisa de
   waiver gate-side — correção declarada do SESSIONEND-NOTE §104-108);
   plano/LEDGER atualizados; `EXPECTED_NOOP_REFS` removida com os DOIS
   consumidores; finalize 4g e LAND V6d INVERTIDOS para asserts de
   AUSÊNCIA (re-embarcar o arquivo passa a abortar a cerimônia); item 2
   do FOLLOWUP → WITHDRAWN (nada mais a entregar), com a gramática de AC
   do bloco histórico neutralizada para não poluir o índice de escopo.

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **332/0** (7.12s) —
`EXPECTED_UNIT_PYTEST_PASSED` 331→332 (+1 controle). Plano principal
segue com 0 checkbox aberto. Refinalize + r15 na sequência.
