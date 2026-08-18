# Principal QA Architect — PLAN-179 round 1

## Verdict
**ADJUST.** A tese e E1/E2 se sustentam verificadas contra o disco linha a linha, mas 4 ACs de teste (W0, W1, W2) citam caminhos que não existem, ignoram um teste que JÁ afirma o comportamento oposto ao que W1 vai produzir, ou pedem prova que a arquitetura de teste do repo não pode honestamente dar.

## Summary

Verifiquei `resolve_plan_id()` (`.claude/hooks/_lib/scratchpad_lib.py:103-165`) — E2 está correto: nenhum fallback existe, a proibição M2 está documentada inline (linhas 122-125), e a exceção `PlanIdDerivationError` é levantada sem degradação. Também confirmei que os hooks `check_precompact_continuity.py`/`check_postcompact_reinject.py` já são **canônicos** (marcador H1 presente 3x no arquivo vivo, não mais staged) — então a suíte que os testa hoje roda contra código de produção real, apesar do nome do arquivo e do docstring dizerem "staged".

O maior problema que encontrei: `.claude/hooks/tests/test_check_compaction_continuity.py:273-281` tem um teste chamado `test_no_plan_transition_degrades_to_unavailable` que afirma **exatamente o bug que W1 vai corrigir**:

```python
def test_no_plan_transition_degrades_to_unavailable(self):
    # A session with no plan_transition → plan_id "unknown", scratchpad skip.
    out = self._run_gate(_pre_hook, {...})
    self.assertEqual(out, {})
    ev = self._audit_events("compaction_continuity_snapshot")[0]
    self.assertEqual(ev["plan_id"], "unknown")
    self.assertEqual(ev["snapshot_outcome"], "scratchpad_unavailable")
```

Este é um teste de regressão que **hoje é verde por proteger o bug**. US5 do plano pede um teste NOVO que "replica E1 e FALHA contra o código de hoje" — mas aponta para `.claude/hooks/tests/test_precompact_continuity.py`, arquivo que **não existe** (grep confirma: o único arquivo real da família com testes PRE+POST gerais é `test_check_compaction_continuity.py`, 19755 bytes, 1 Jul; existe um segundo arquivo, `test_postcompact_reinject_no_exec_payload.py`, mas é dedicado inteiramente a payload-poisoning/exec-safety, não a comportamento geral de reinjeção). Se W1 for executado seguindo o path literal do plano, dois desfechos ruins são possíveis: (a) alguém cria um arquivo novo isolado, o teste antigo continua verde e vira uma afirmação morta sobre um comportamento que não existe mais — ou pior, entra em contradição silenciosa; (b) ninguém edita o teste antigo e ele **quebra no CI no momento em que W1 landa**, sem que nenhum AC do plano tenha previsto isso.

## Risks

1. **[P0] `test_no_plan_transition_degrades_to_unavailable` não está no escopo de W1** — `test_check_compaction_continuity.py:273-281`. Este teste assevera `snapshot_outcome == "scratchpad_unavailable"` para exatamente o cenário que a US3 (fallback por sessão) muda. W1 lista como alvo de US5 um arquivo inexistente (`test_precompact_continuity.py`) e não toca este arquivo real. Sem edição explícita, o merge de US3 quebra CI ou (se alguém "conserta" apagando o assert sem registrar por quê) apaga a única prova viva de que o bug existia. **Must-fix.**

2. **[P1] Caminho de arquivo errado em 3 ACs de teste.** `.claude/hooks/tests/test_precompact_continuity.py` (US5) não existe; o real é `test_check_compaction_continuity.py`. US5d cita `test_postcompact_reinject.py` — também não existe; os dois arquivos reais da família são `test_check_compaction_continuity.py` (comportamento geral PRE+POST, inclui `test_reinjects_pointers_via_additional_context`, `test_pointers_only_no_plan_body_injected`) e `test_postcompact_reinject_no_exec_payload.py` (dedicado a payload-poisoning/exec-safety — classes distintas: `TestPoisonedPayloadNeverExecutedOrExpanded`, `TestFrozenPointerTemplate`, `TestPayloadChannelsStayDead`). Escrever o AC contra nomes errados é o tipo exato de erro que a lição `[[feedback-verify-counts-real-path-is-local]]` já registrou noutra superfície deste mesmo repo — "cura no corpo ≠ cura nas referências", aqui é "referência de teste ≠ arquivo real". Corrija os 3 usos e decida explicitamente onde o pinning adversarial de US5d entra: comportamento geral (`test_check_compaction_continuity.py`) ou um terceiro arquivo dedicado a pinning (a classe de teste mais próxima, por tema, é `TestPayloadChannelsStayDead` — mas ela testa payload malicioso, não restrição fixada; são propriedades diferentes).

3. **[P1] A suíte de continuidade usa um padrão dual-loader staged/canonical não mencionado no plano** (`_pick()`, `test_check_compaction_continuity.py:61-75`, herdado do PLAN-135 W2). Um teste novo escrito ingenuamente (import direto do hook) quebra essa convenção — ou fica desalinhado dela e passa a ser o único teste da família que não segue `_pick()` + `TestEnvContext` + o `_AuditEmitSlotGuard` (linha 116). US5/US5d precisam dizer explicitamente "estende o arquivo existente, não cria um novo", ou justificar por que um novo arquivo é correto — mas isso deve ser uma decisão nomeada, não um acidente de porque ninguém leu o arquivo real primeiro.

4. **[P1] US5d (controle adversarial) pede uma prova que a arquitetura de teste não pode dar honestamente.** O próprio plano admite: "o sumarizador é o harness, não é mockável". Isso significa que um teste unitário NÃO PODE provar a claim comportamental do paper (0%→30%/59% de violação pós-compactação) — só pode provar uma claim ARQUITETURAL: que as restrições fixadas nunca fazem parte do que É ENVIADO ao sumarizador (ou seja, chegam por um canal que não passa pela compressão, e portanto sobrevivem por construção, não por sorte do modelo). O anti-padrão da própria skill que carrego (`testing-strategy/SKILL.md` — "Mock everything: Tests pass but system broken") se aplica ao inverso aqui: se o "controle adversarial" mockar o sumarizador para "provar" que ele preserva as regras, o teste vira vacuous — prova a mecânica do mock, não do sistema. Recomendo reescrever a AC de US5d como: "as restrições fixadas são entregues por um canal que NUNCA participa do bloco compactado (prova estrutural: assert de que o payload pinned não está no transcript que seria enviado ao `compact_20260112`), independente de qualquer transcript hostil no restante do contexto." Isso é testável determinística e honestamente; "o modelo não vai ser enganado" não é.

5. **[P1] W0-1 (sonda do canal) não tem protocolo reprodutível declarado.** O plano diz "controle positivo obrigatório: a sonda deve FALHAR quando o canário não é emitido" — correto e alinhado com `[[feedback-probe-needs-neutral-user-layer]]`. Mas "forçar `/compact` manual" é, pelo próprio texto do plano (E1), uma operação PAGA e não-determinística de disparar. Falta: (a) declarar que este é um script operator/local (nunca CI), na mesma classe de `council`/`council-audit` deste repo; (b) idempotência — o que acontece se a sonda rodar duas vezes seguidas (audit-log ganha 2 eventos `context_pressure_observed`? Isso contamina a medição de US2 que a mesma wave está tentando fazer com números limpos). Sem isso, W0-1 mede sua própria sonda, não o canal.

6. **[P2] Medição de `F` (US2) é só parcialmente mensurável pela ferramenta citada.** `context-budget.py` mede só arquivos do repo via heurística chars/4 — CLAUDE.md, PROTOCOL.md, team.md, skills. O `F` da fórmula do plano inclui explicitamente "system prompt + defs de ferramenta" — nenhum dos dois é um arquivo do repo; nenhum script deste repo os mede. A AC de saída do W0 promete "`F` e `T` têm valores medidos" — isso só é verdade para a metade de `F` que é Gate 1+2+índice (40.116+4.413, já medido). A outra metade (system prompt + tool defs) precisa de uma fonte de medição nomeada (ex.: `usage.iterations[]` de uma chamada real, citado na própria pesquisa §1.1) ou a AC continua parcialmente uma estimativa disfarçada de medição — a mesma classe de falha que `[[feedback-measurement-must-list-its-inputs]]` já pegou noutro lugar deste repo.

7. **[P2] `context_pressure_observed` (US2) não tem AC de fechamento de enum.** O padrão do repo para toda action nova em `audit_emit.py` é: branch `_scrub_` dedicado + `_ALLOWLIST` própria + par de testes tipo `test_compaction_actions_not_in_passthrough` / `test_compaction_actions_registered` (`test_check_compaction_continuity.py:439,444`) que provam que a action está no dispatch-gate e NÃO no passthrough genérico. Sem essa AC nomeada, "enum fechado" é alegação, não propriedade testada — mesma lição que W1-b já cita para pinning (US5d), aplicada aqui também.

8. **[P2] OQ-4 (inflação do audit-log) — resposta:** emitir `context_pressure_observed` em "toda pressão de contexto" vai inflar o log de 2,1 MB rapidamente se o gatilho for por turno. Recomendo amostragem por CRUZAMENTO DE FAIXA (emitir só quando `used_bucket` muda de valor, não a cada leitura) — histerese, não sampling aleatório. Isso também simplifica o teste de fechamento do item 7 (um enum de buckets é mais fácil de fechar que um float contínuo, e evita a classe de bug de `[[feedback-float-in-hmac-field-drops-whole-event]]` se o campo cair sob HMAC).

## Must-fix

- Editar `test_check_compaction_continuity.py:273-281` como parte EXPLÍCITA de US3/US5 (não é opcional; é o teste que a mudança de comportamento invalida).
- Corrigir os 3 caminhos de teste citados (US5, US5d) para os arquivos reais; decidir e nomear se W1-b usa um arquivo novo dedicado a pinning ou estende os existentes.
- Reescrever a AC de US5d como propriedade ARQUITETURAL testável (canal pinned nunca participa do payload compactado), não como afirmação comportamental do sumarizador.
- W0-1: nomear o script como operator/local-only (nunca CI) e declarar idempotência/contagem de execuções antes que US2 dependa dos números que ele produz.
- US2: nomear a AC de fechamento de enum (par not-in-passthrough/registered) e a fonte de medição para a metade de `F` que `context-budget.py` não cobre.

## Nice-to-have

- Amostragem por buckets/histerese em `context_pressure_observed` em vez de emissão livre (responde OQ-4 com um desenho concreto, não só "sim, precisa de sampling").
- W2: nomear a action de audit que torna a OMISSÃO do ledger-checkpoint visível (espelhando `spawn_file_assignment_recorded` do ADR-191), já que "advisory primeiro" sem instrumento de visibilidade repete a classe que o próprio `team.md` já resolveu noutro guard.
- Declarar protocolo reprodutível de "matar sessão no meio" para o ensaio de W2 (kill -9 vs Ctrl-C vs fechamento de terminal têm efeitos diferentes sobre quais hooks disparam).

## Unseen

O plano não menciona `pytest -n auto` nem risco de flake para os hooks novos. Não verifiquei se as `_ALLOWLIST` de `audit_emit.py` são constantes de módulo imutáveis (se alguma for mutada em runtime por um hook, xdist workers paralelos podem colidir) — recomendo essa checagem pontual antes de W0 escrever a primeira action nova, mas não achei evidência de que seja um risco real, só não descartei.

## What I would NOT change

A skill que carrego reforça "happy path only" como anti-padrão — e este plano é o oposto disso: E1 é, por construção, um teste de caminho de falha real medido em produção, não hipotético. Não mudaria a decisão de manter os testes existentes como fonte de verdade sobre o comportamento ATUAL (o Must-fix #1 é para EDITAR, não descartar, esse teste) — apagar `test_no_plan_transition_degrades_to_unavailable` sem substituí-lo por uma asserção do NOVO comportamento perderia a única prova regressiva de que o bug existiu. Também não mudaria a decisão de W0 ser gate de tudo — dado que já achei uma lacuna real de medição (`F` parcial) que só W0 pode fechar, adiantar W1 sem W0 seria repetir a classe "branch-local-patching-induces-regressions" que o próprio repo já nomeou.

DONE_WITH_CONCERNS
