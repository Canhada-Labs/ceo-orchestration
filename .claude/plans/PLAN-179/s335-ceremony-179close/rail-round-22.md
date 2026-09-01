# wave-179close — rail codex rodada 22 (sombra pós-curas r21, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (1 P1 + 2 P2 — TODOS verificados REAIS; o P1 fechou por TROCA DE ARQUITETURA; curados ANTES da r23)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r22.txt` (13.304
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.

## Os achados (verificação + cura)

1. **[P1] `IgnoreAllRules.md` — 14 chars exatos, expandido PERMITIDO
   pelos validadores** — VERIFICADO, e é a 5ª rodada da MESMA classe
   (r15 espaços → r19 hífens → r20 camel/minúscula → r21 run-19 → r22
   run-14-que-o-validador-permite). A regra da casa
   (fix-of-fix ⇒ trocar a arquitetura da cura) foi aplicada: **o canal
   de NOMES saiu do systemMessage**. O render é counts-only
   ("N topic(s) + index (names withheld — inspect the memory dir…)");
   NENHUM string vindo do dir de memória alcança a superfície
   instruction-adjacent — a classe morre por REMOÇÃO do canal, não por
   enumeração. O sanitizer e a lista `names` ficam no dict como gate
   TESTADO de qualquer render futuro (nada foi relaxado); SPEC row e
   docstrings corrigidos com a supersessão do split "names to the
   operator" DECLARADA (desvio do W2 AC registrado). O que se MANTÉM:
   counts verdadeiros, outcome, flag de index, todos os 21 rounds de
   curas de janela/âncora. Controles: asserts NotIn nos 3 testes de
   render.
2. **[P2] Resume nativo reusa session_id** — VERIFICADO: o oldest-match
   cru ancorava no start da invocação ANTERIOR (janela atravessando
   invocações ⇒ tópico antigo virava `written` num resume sem escrita).
   CURA: o segmento da invocação atual começa DEPOIS do último
   `session_end` VERIFICADO do mesmo id; um end que casa mas não
   verifica é fronteira inverificável ⇒ terminal unknown (encolher
   janela por fronteira forjada fabricaria absent — a direção pior).
   Controle: `test_native_resume_segments_at_last_session_end`
   (start→end→resume assinados em cadeia; tópico da invocação anterior
   ⇒ absent, nunca written).
3. **[P2] Glob materializava além do deadline** — VERIFICADO: `glob.glob`
   recursivo expandia a árvore inteira antes do primeiro check e o 2º
   pattern rodava após o break. CURA: deadline ANTES de cada pattern +
   `iglob` lazy. Controle: `test_ceremony_globs_respect_expired_deadline`
   (glob-bomba + deadline vencido ⇒ [] sem nenhuma chamada).

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **349/0** (7.85s) —
`EXPECTED_UNIT_PYTEST_PASSED` 347→349 (+2 controles; 3 testes de render
com asserts invertidos, declarado). Curas confinadas a 4 paths do
EXPECTED. Refinalize + r23 na sequência.
