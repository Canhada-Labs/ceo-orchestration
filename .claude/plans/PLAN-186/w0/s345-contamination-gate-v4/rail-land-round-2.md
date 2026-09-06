Rail-Verdict: APPROVE

Nota da rodada (mecanismo + texto, DUAS lanes codex `gpt-6-astra` esforco max, em
paralelo, sobre a arvore VIVA nao-commitada): dois defeitos REAIS da rodada 1 e um P1
meu da rodada 2 foram CURADOS; os dois P2 restantes sao residuais declarados, cada um
com raio de acao MEDIDO como zero neste repositorio. Nenhum P1 sobrevive.

Pack: contamination-gate-v4 (PLAN-186). Land livre — os 4 paths do pack tem oraculo
`--is-canonical` = 0; nenhuma assinatura devida e NENHUMA foi feita (noite sem o Owner).

## Regra de parada PRÉ-REGISTRADA (escrita ANTES de ler qualquer saída das lanes)

Rodada 1 do rail do LAND, duas lanes codex (`gpt-6-astra`, esforço `max`) em
paralelo sobre a árvore VIVA não-commitada, cujo diff é exatamente os 5 paths
que vão ao commit.

1. **P1 NOVO dentro dos 5 paths** (fato errado num byte commitado, código
   quebrado, gate que ficaria vermelho na CI, path pessoal absoluto) ⇒ cura NO
   DERIVADOR do pack (nunca à mão na árvore viva), re-aplicar, re-rodar bateria
   e gates, e UMA rodada de confirmação (r2 é o teto absoluto). Se a cura pedir
   mais de uma iteração, o pack é DROPADO e a árvore restaurada.
2. **Achado FORA dos 5 paths** (arquivo canônico, rota de upgrade do adopter,
   parsing dependente de runner do GitHub) ⇒ RESIDUAL DECLARADO, com o texto do
   codex citado e a minha verificação em disco ao lado.
3. **Redação / gosto / P3** ⇒ RESIDUAL DECLARADO.
4. Uma rodada cujos achados sejam TODOS residuais termina
   `Rail-Verdict: APPROVE` com a lista abaixo da linha. Nunca reetiquetar um P1
   para landar; nunca APROVAR rodada incompleta.
5. **Liveness:** cada lane só é lida quando `lsof` sobre o seu arquivo de saída
   não mostra escritor E o arquivo termina no seu próprio bloco terminal
   (`Full review comments:` ou uma declaração explícita de ausência de defeitos,
   para a lane de mecanismo; a própria linha `tokens used`, para a de texto).
   Saída com `Selected model is at capacity` / `Review was interrupted` = rodada
   MORTA (não é registro); `usage limit` = quota morta, parar de lançar codex.

## Rodada 1

Lane de MECANISMO (`codex exec review --uncommitted`) — verdito proprio:

> APPROVE. No actionable regressions found. All 307 contamination tests passed on
> Python 3.9.6, along with the contamination and test-environment hygiene checks.

Lane de TEXTO — `REJECT`, DOIS achados, ambos reproduzidos em disco antes de aceitos:

* **[P1] escopo do digesto.** Citado: «`8d7cf879…` … calls it the staged-diff digest.
  The complete five-file staged diff hashes to `ab2d9c8c…`.» VERIFICADO: o diff staged
  completo hasheia `ab2d9c8c…` e o dos 4 paths do pack `8d7cf879…`. A linha era MINHA
  (bookkeeping do passo 7), nao do pack. CURADA nomeando o escopo.
* **[P2] falha do walker fora da redacao.** Citado: «catches only
  `PersonalPathUnreadable` … produces rc 1 and an uncaught traceback containing the
  personal absolute checkout path on stderr.» VERIFICADO com injecao de
  `PermissionError` no walker: excecao NAO capturada, e os frames do traceback — que
  o interpretador imprime, fora do alcance de qualquer redacao interna — carregam o
  path absoluto do checkout. CURADA **NO DERIVADOR** (`except OSError` saindo pelo
  mesmo funil sanitizado, rc 2, mensagem `FATAL: cannot enumerate in-scope files:
  <redacted: names a home directory>`), mais DOIS testes de controle positivo no
  payload (`TestWalkerFailureIsSanitised`, subclasse de `TestEnvContext` — a primeira
  redacao como `unittest.TestCase` foi reprovada pelo `check-test-env-hygiene` e
  corrigida tambem no derivador). Probe pre-cura: excecao NAO capturada. Pos-cura:
  rc 2, sem `Traceback`, sem o segmento do dono.

## Rodada 2 (confirmacao, sobre os bytes finais)

Lane de TEXTO — `REJECT — one P1`, e ele era meu:

* **[P1] digesto do payload defasado.** Citado: «The current four-file staged diff
  hashes to `94e5d4fe…`. I reproduced `5367ef9f…` exactly by reverting the new test
  class to `unittest.TestCase` in memory.» VERIFICADO: exatamente isso — eu medira o
  digesto ANTES da correcao da classe-base. CURADO com o numero medido por ela e
  reconferido por mim. A mesma lane confirma a cura (2): «injected walker errors
  return sanitized rc 2 without traceback or owner leakage. Existing handled exits
  remain intact. No additional P2/P3 findings.»

Lane de MECANISMO — `REJECT`, DOIS P2 NOVOS. Ambos reais, ambos VERIFICADOS por mim,
ambos **residuais declarados** por raio de acao medido e por serem mudanca de
ARQUITETURA, fora do que um lander decide sozinho numa noite sem o Owner:

* **[P2] ativo binario legitimo em escopo.** Citado: «For an adopter with a normal
  `docs/logo.png`, this rejects the entire scan because valid PNGs contain NUL
  bytes.» MEDIDO aqui: **0 de 2209** arquivos rastreados em escopo (`docs/`,
  `.claude/plans/`) contem NUL — a CI deste repo nao muda de cor. O efeito e sobre o
  ADOPTER, a mesma familia do residual ja declarado «o allowlist nao sobrevive ao
  `upgrade.sh`», cuja cura vive em arquivo CANONICO. E reverter o fail-closed
  desfaria a cura da rodada 18 (um documento UTF-16 lido LIMPO): trocar isso e
  decisao de arquitetura do dono do pack, nao cura de land.
* **[P2] termo privado dentro do PATH de uma linha honrada.** Citado: «When a waived
  filename contains a configured private term, this prints that term verbatim:
  `_personal_path_mask_rel` only masks home-directory owners.» VERIFICADO na leitura
  do codigo. MEDIDO aqui: a Regra 1 esta VERDE (`✓ No contamination outside allowed
  zones`), logo nenhuma das **242** linhas honradas carrega termo privado no path.
  Ampliar a redacao para a dimensao da Regra 1 e uma dimensao NOVA de mascara —
  arquitetura, e o pack acabou de pagar (rodada 24) o preco de mexer nessa mascara.

## Liveness das quatro lanes

Cada saida foi lida so depois de `lsof` nao mostrar escritor. Cabecalho proprio do CLI
`model: gpt-6-astra` nas quatro. Mecanismo r1/r2: bloco terminal proprio (declaracao
explicita de ausencia de defeitos em r1; `Full review comments:` em r2). Texto r1/r2:
linha `tokens used` propria (142.835 e 143.277 — valores DIFERENTES, logo nao e cache
hit). Zero ocorrencias de `Selected model is at capacity` / `Review was interrupted` /
`usage limit` como saida das lanes; as 2 ocorrencias em `codex-r2-text.txt` sao CITACAO
dos documentos do proprio pack, verificadas linha a linha.

## Bateria sobre os bytes finais

Toda ela DEPOIS da ultima edicao. `check_contamination.py` rc 0 com 242 linhas honradas
(digesto do conjunto `6b31eb8d…`) e `--fail-on-stale` rc 0; pytest dos 3 modulos de
contaminacao **309 passed** e do modulo de path pessoal **269 passed** (307/267 antes
da cura; os 2 novos sao os controles positivos dela); 8 probes de cura exit 0;
diferencial v3-vs-v4 **8/8 OK**; 2.a aplicacao rc 1 RECUSADA com 14 causas nomeadas;
6 gates de corpus rc 0 sobre a arvore STAGED (`validate-governance.sh` COMPLETO com
`Errors: 0`; `verify-counts.sh` sem drift; claims; staleness; env-hygiene; contaminacao).
Suite completa de `.claude/scripts/tests/`: 1 vermelho PRE-EXISTENTE e alheio
(`test_skill_patch_propose.py::test_diff_size_cap_enforced_with_many_lessons`), ja
registrado na S343 e nas linhas de progresso anteriores deste plano.
