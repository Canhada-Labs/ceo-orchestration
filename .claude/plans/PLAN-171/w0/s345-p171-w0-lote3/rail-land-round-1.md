Rail-Verdict: APPROVE

# Rail do LAND combinado — rodada 1 (S347, noite autônoma, 2026-09-06)

Pack landado: **p171-w0-lote3** (PLAN-171 W0, lote 3/6). Base `db05586`
(= `origin/main` no momento do land). Uma rodada, DUAS pistas codex em
paralelo pelo gate compartilhado, ambas concluídas ANTES de qualquer
`APPROVE`, `commit` ou `push` (classe S345-d).

## Critério de parada PRÉ-REGISTRADO (escrito antes de ler as saídas)
- P1 NOVO dentro dos paths do pack ⇒ cura no derivador + UMA rodada (teto).
- Achado de redação, fora dos paths do pack, ou follow-up já NOMEADO ⇒
  residual declarado, com o texto do codex citado e a verificação em disco.
- Rodada só com residuais termina `Rail-Verdict: APPROVE` com a lista abaixo.
- Nunca re-rotular um P1; nunca APROVAR com uma pista ainda viva.

## Diff revisado (exatamente os paths landados)
```
A  .claude/plans/PLAN-171/w0/lote-3-S347.md
M  .claude/plans/PLAN-186-orchestrator-operating-model.md
```
A pista de mecanismo imprimiu esse MESMO conjunto no seu próprio
`Status after checks`, e verificou por `git show :<path>` que os bytes
staged são os bytes revisados (`True` nos dois).

## Pista 1 — mecanismo (`codex exec review --uncommitted`, sandbox workspace-write, effort max)
- Liveness: cabeçalho próprio com `model: gpt-6-astra`; `Selected model is
  at capacity` = 0, `Review was interrupted` = 0, `usage limit` = 0.
- A única ocorrência de `Full review comments:` no arquivo está DENTRO de
  um trecho do `CLAUDE.md` que a revisão ecoou (l. 1490) — não é o bloco
  terminal da própria revisão. O bloco terminal é a declaração explícita
  de ausência de defeito.
- Veredito, verbatim:
  > APPROVE. The changes are limited to the census report and commit
  > metadata. The nine referenced positive controls pass, and no
  > actionable defects were identified.
- **Zero achados.**

## Pista 2 — texto (brief sobre as claims + EVIDENCE, sandbox read-only, effort max)
- Liveness: cabeçalho próprio com `model: gpt-6-astra`, `tokens used`
  presente (1), `at capacity` / `interrupted` / `usage limit` = 0/0/0.
- Veredito, verbatim:
  > APPROVE — no P1/P2 findings in the two staged files.
  > Counts, partitions, citations, Appendix C greps, and `db05586`
  > provenance check out. Read-only validators passed.
- **Zero achados P1/P2.**

## Residuais declarados (nenhum é P1; cada um verificado em disco por mim)
1. **Esclarecimento da pista de texto**, verbatim:
   > The 49 registrations count Python-file commands; settings contains 50
   > total entries, including one inline `echo`.
   Verificado em disco: o oráculo de contrato do `validate-governance.sh`
   COMPLETO imprime, nesta mesma árvore,
   `hook-stdout-schema: 48 wired script(s), 49 registration(s), 0
   violation(s)` — exatamente a grandeza que o relatório publica
   (registrações de SCRIPT de hook). A 50.ª entrada do `settings.json` é
   um comando `echo` inline, que não registra script e por isso não entra
   em `|L|`/registrações. O número publicado está certo para a grandeza
   definida; a nota é vocabulário, não defeito.
2. **Escopo da pista read-only**, verbatim:
   > Mutation tests and the full write-producing battery were not rerun
   > under the read-only restriction.
   Coberto pela bateria do lander: metade VERMELHA 9/9 rc=1 e o replay do
   mutante da linha 10 rodaram numa worktree descartável em `db05586`, com
   o conjunto de neuters IDÊNTICO ao baseline do pack.
3. **Linha de progresso do lote 3** no `PLAN-171-governance-imports-provenance.md`
   NÃO é escrita por este land — decisão do CEO no `STATE.md` do pack, aceita
   pelo refutador: ela é devida ao PRÓXIMO pack de W0.
4. Lotes 4-6 = `R[20:42]` (22 hooks) — fora deste lote por desenho.
5. Follow-ups MEDIDOS e nomeados no relatório: `check_cost_envelope.py`
   bloqueia e nenhuma medição demonstra um controle desse bloqueio
   (`sem controle`); três testes em forma de enforce de
   `test_check_confidence_gate.py` são `@unittest.skip` (66/286/316).

## Bateria reproduzida pelo lander em `db05586` (rc lido direto, sem pipe)
- metade VERDE sobre os 9 node ids exatos: `9 passed`, rc 0
- metade VERMELHA (worktree descartável): 9/9 rc=1, conjunto de neuters idêntico
- replay do mutante da linha 10: intacto `systemMessage=True` → mutante `False` → restaurado `True`
- `gen-count.py` normal rc 0 reproduz a linha de contagem publicada
- `gen-count.py --plant` (controle VERMELHO) rc 1: 10→11, 9→10 e RECUSA
- greps do Apêndice C re-executados no arquivo APLICADO: 6 padrões, 0 mismatches
- node ids da tabela == conjunto que rodou: IDENTICAL (9)
- `check_plan_edit.py` sobre os bytes shipados: `{}` rc 0
- `validate-governance.sh` COMPLETO: `PASS`, `Errors: 0`
- `verify-counts.sh` rc 0, exatamente 1 `no drift detected`
- `check-claude-md-claims.py` / `check-staleness.py` / `check-test-env-hygiene.py` / `check_contamination.py`: rc 0
- `grep -c` no arquivo shipado: `/Users/` = 0, `/var/folders` = 0
