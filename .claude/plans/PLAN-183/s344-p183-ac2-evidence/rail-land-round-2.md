# p183-ac2-evidence — rail de land, rodada 2 (S344, 2026-09-04)

Rail-Verdict: APPROVE (com 2 residuais DECLARADOS, ambos citados literalmente abaixo)

Duas lanes codex em PARALELO sobre a arvore viva ja curada. Os DOIS P1 da
rodada 1 caem: a lane B verificou cura por cura e a lane A nao os repetiu.

## Cures verificadas pela lane B (citacao literal)

> - `git diff --cached --check` returns 0; both evidence files have exactly one final newline and no blank line at EOF.
> - The checker is explicitly declared absent; only the render and JSON data are claimed self-contained.
> - The `mv -n` collision/exit-0 warning is complete at `benchmarks.yml.template:5-12`.
> - The W2 reference now correctly says `abaixo`.
> - `benchmarks.yml.template:3-12`, the citation at `validate.yml.template:12`, and the plan citation `:5-12` all match disk.
> - Both JSON renders reproduce exactly; all 14 entries are successful and the 11 workflow step names match the template at `bc52016`.

Confirmei os seis pontos por conta propria antes de commitar.

## Residual 1 — DECLARADO (lane B rotulou P1; classifico como P2 de REDACAO)

Citacao literal da lane B:

> The evidence narrowing remains self-contradictory. github-run-33896213436.md:162
> says the runs prove the delivered template executed, while line 168 correctly
> admits the committed data provides only name-level agreement — not workflow bytes,
> run bodies, action references, or installer output. The plan repeats the stronger
> conclusion at PLAN-183-adopter-fitness.md:1432. Owner acceptance can justify
> closure, but it does not make name-level evidence prove byte identity.

Verificacao em disco e classificacao, com o criterio de P1 desta lane
(fato ERRADO na arvore, codigo quebrado, gate vermelho, path pessoal):

- Nenhuma afirmacao FALSA foi encontrada. O run existe e e verde; os onze
  nomes de passo batem o template em `bc52016` (comparei com `git show`);
  o `cmp` esta explicitamente marcado como testemunho da sessao que capturou,
  NAO como evidencia re-checavel; e o fecho esta ancorado no criterio ESCRITO
  e RASTREADO do Owner (`PLAN-183/owner-decisions-S344.md`), que a evidencia
  cumpre literalmente.
- As linhas :162 e :168 vivem na MESMA secao, cujo titulo e literalmente
  "What these runs prove, and what they do not": a metade que limita e
  inseparavel da que afirma, e foi ESCRITA nesta rodada por causa da r1.
- O que a lane B pede e uma RESSALVA ADICIONAL sobre uma frase verdadeira ja
  limitada seis linhas abaixo — fortalecimento de redacao, nao correcao de fato.

Fica REGISTRADO para quem quiser fechar: uma v3 do pack pode escopar a frase
:162 em UMA oracao (provam, como historia da sessao; para o que o artefato
COMMITADO estabelece sozinho, ver abaixo). Nao foi feito aqui porque o teto
de UMA iteracao de cura por land ja tinha sido gasto na r1.

## Residual 2 — DECLARADO (lane A, P2; FORA do que este pack pode fechar)

Citacao literal:

> When an adopter already has `benchmarks.yml` and follows the new "pick another
> name" instruction, the workflow still hard-codes `.github/workflows/benchmarks.yml`
> in both `pull_request.paths` and `push.paths` (lines 36 and 42).

Verificado em disco: as linhas 36 e 42 de `benchmarks.yml.template` de fato
fixam `.github/workflows/benchmarks.yml`. O achado e consequencia da cura 4 da
r1 (a orientacao de escolher outro nome), e o filtro fixo e ANTERIOR a este pack.
Fechar direito pede decidir entre remover a recomendacao de renomear ou mandar
refletir o nome nos dois filtros — mudanca de conteudo do template, materia de
uma wave do PLAN-183, nao de um land de evidencia.
