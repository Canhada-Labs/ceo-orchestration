# Pair-rail prompt — PLAN-194 W1, CI pronto para o Ubuntu 26.04 (Codex, read-only, cold)

Você é o revisor cruzado (V2 da cascata de verificação — `PROTOCOL.md` §Verification cascade).

**Sujeito desta rodada (e só ele):**
1. o patch `.claude/plans/PLAN-194/wave-w1/w1.patch` — JÁ APLICADO nesta árvore: o
   `.github/workflows/validate.yml` está aqui na pós-imagem; a pré-imagem é o `index` do patch. A
   cópia `.claude/plans/PLAN-194/wave-w1/staged-w1/.github/workflows/validate.yml` é o mesmo conteúdo
   (mesmo blob; o SIGN confere);
2. o texto que o Owner vai assinar, `.claude/plans/PLAN-194/wave-w1-approved.md` (os campos
   `TO-FILL-BY-SIGN` são preenchidos pelo script de assinatura; não são achado);
3. o controle `.claude/plans/PLAN-194/wave-w1/check-w1-shape.py` e o registro dele,
   `red-control.txt` (vermelho no `validate.yml` anterior, verde no novo).

**O que a W1 pede (PLAN-194, seção W1, verbatim dos itens):** «W1.1 perna 3.9 do
`hook-tests-python-matrix` num rótulo fixo `ubuntu-24.04` (hoje o job inteiro é `runs-on: Ceo`); as
outras pernas seguem onde estão.» «W1.2 os `import yaml` de `:304-305` deixam de depender de PyYAML do
sistema (mover para depois do `setup-python` de `:467` ou instalar PyYAML antes).» «W1.3 uma perna
3.14 em `ubuntu-26.04` só no `schedule` (`validate.yml:14-15`, cron `37 7 * * *`), para detectar quebra
do sistema novo antes dos adopters.» Fora da letra do plano, declarado no texto assinável: o timeout
por perna (45 min nos runners padrão, 25 no `Ceo`).

**Critérios:**
- as expressões `${{ }}` de `runs-on`, `timeout-minutes` e da matriz dão, para push, pull_request e
  schedule, exatamente: 3.9 → `ubuntu-24.04`/45; 3.10–3.12 → `Ceo`/25; 3.14 → `ubuntu-26.04`/45 e só
  no schedule; push = 3.9+3.12; pull_request = as quatro (a precedência de `&&`/`||` do Actions e a
  conversão do resultado para número no `timeout-minutes`);
- nada mais muda no comportamento do job `validate` além da POSIÇÃO do step dos catálogos (corpo
  byte a byte igual), e a nova posição usa o PyYAML instalado pelo `pip` do próprio job;
- o actionlint do CI (1.7.7, nas duas formas de invocação: a do job `validate` e a do
  `actionlint.yml`) aceita o arquivo; o lint não confere rótulo dentro de expressão — isso está
  declarado como residual, e precisa estar;
- nenhum outro job, gatilho, `concurrency`, permissão ou pin de action muda;
- CADA frase do texto assinável é uma afirmação sobre o patch ou sobre a medição: uma afirmação FALSA é
  motivo de NO-GO; o «Residual declarado» precisa ser verdadeiro e completo para a mudança.

**Regra desta rodada:** a regra de parada pré-registrada é de no máximo 3 rodadas; a rodada 3 é a
final. NO-GO só por P0 ou por afirmação falsa no texto assinável. Relate todo P1/P2 com
`arquivo:linha` e cura concreta. Não altere arquivos (sandbox read-only).

**Saída:** a lista de achados, cada um com severidade `P0 | P1 | P2`, `arquivo:linha` e cura; se não
houver nenhum, escreva exatamente `NENHUM ACHADO`. Termine com UMA linha
`VERDICT: GO | GO-WITH-CONDITIONS | NO-GO`.
