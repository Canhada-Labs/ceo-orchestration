# Crítica — Principal Security Engineer (VETO)

> Rodada 2 do debate do PLAN-184. Rótulo anonimizado na síntese: **Critic-B**
> (mapa em `anonymization-map.md`). Eixo desta crítica: governanca e superficie de ataque: markdown normativo, fail-closed real, bypass por escolha de path.
> Agente read-only (ADR-136-AMEND-1): não editou arquivo nenhum;
> toda claim foi verificada contra o disco antes de entrar aqui.

## Verdict

**ADJUST_PROCEED**

## Summary (≤ 3 bullets)

- O MECANISMO esta certo e verifiquei que o split e mecanicamente limpo: nenhum `needs:` entre os 7 jobs, nenhum secret, nenhum `workflow_run` de outro workflow sobre validate.yml, e nenhum script/gate fixa os 4 job-ids ao arquivo (so 2 docstrings + 2 ADRs). Rota C sobrevive a critica.
- Os NUMEROS nao sobrevivem. Medi os dois fatores da economia: (a) na granularidade que `paths-ignore` realmente avalia — o diff do PUSH, nao do commit — 85 dos 167 runs sao pulaveis com uma denylist compativel com a §4, nao 106 (98 mesmo com `docs/**`, que a §4 proibe); (b) os minutos por job da §1 estao falsificados por medicao direta: formal = 15s (nao 4,7 min), E2E = 1m43s (nao 3,4 min). A1 real ~US$4,3/dia contra manchete US$9,24 — 54% de divergencia, e o AC-6 dispara sozinho.
- Faltam as duas coisas que fazem um filtro sobreviver ao tempo: BACKSTOP (o proprio precedente citado, coverage.yml:15, tem `schedule:` nightly — e ownership-nightly.yml:6-8 registra que schedule IGNORA paths; o plano copiou o filtro e deixou a rede) e MANUTENCAO (zero instrumento recorrente para o drift da denylist). E a execucao esbarra na cerimonia canonica: `.github/workflows/*.yml` esta no guard list e o plano nao a menciona uma vez.

## Must-fix (blocking) — P0

### F-01 — Todo alvo de escrita das W0/W1/W2 e canonical-guarded, e o plano nao menciona a cerimonia uma unica vez

**Como falha.** `.claude/hooks/check_canonical_edit.py:184-185` lista `.github/workflows/*.yml` e `*.yaml` no guard list, e `:178` lista `.claude/adr/ADR-*.md`. A logica (docstring :26-34) e: path canonico sem `approved.md` com `Approved-By:` valido e o path declarado no bloco `Scope:` -> BLOCK do Edit/Write. O commit de split da W1 toca, no minimo, quatro paths guardados (validate.yml, o workflow novo, ADR-021, ADR-050); a W2 toca validate.yml de novo; e ate a rota de medicao 'US$ 0' da W0-US3 ('um workflow de medicao efemero') cria um arquivo sob `.github/workflows/` — tambem guardado, porque o matcher e por PATH, nao por branch. Consequencia concreta: a primeira ferramenta de escrita da W0 volta bloqueada, e o agente de execucao ou trava ou contorna por Bash — exatamente a classe que o guard existe para impedir. Alem disso o frontmatter `:12` afirma `W0-W2 nao esperam nada externo` e `:10` `budget_sessions: 2`, quando a assinatura do sentinel e do Owner com a chave GPG real (a memoria do repo registra 2 cerimonias ja pendentes de GPG desde a S319): o caminho critico declarado esta falsificado. `grep -ci 'cerim|sentinel|canonical|gpg'` no plano inteiro = 0.

**Evidência.** .claude/hooks/check_canonical_edit.py:178,184-185 + docstring :26-34; PLAN-184:10,12; `grep -ci "cerim\|sentinel\|canonical\|gpg" .claude/plans/PLAN-184-ci-cost-routing.md` -> 0

**Cura proposta.** Abrir a W1 (e a W0-US3, se a rota do workflow efemero for escolhida) com um item [P0] de cerimonia: bundle architect + `approved.md` assinado cujo `Scope:` enumere os 4-5 paths guardados do commit de split, ANTES de qualquer edicao. Corrigir `external_wait:` no frontmatter para nomear a assinatura do Owner como espera externa de W1/W2, e somar a cerimonia ao budget_sessions.

### F-02 — Os dois fatores da economia estao falsificados por medicao: 85 pushes pulaveis (nao 106) e 48 min pesados por run (nao 65,4)

**Como falha.** FATOR 1 — granularidade. `paths-ignore` no gatilho `push` avalia o diff do PUSH (`before...after`), nao do commit. Simulei isso com os 167 head-SHAs reais da janela (todos presentes localmente) e o diff entre heads consecutivos: 20 dos 167 pushes carregam mais de um commit (um com 21). Com denylist `.claude/plans/** + .claude/adr/** + *.md de raiz`, pulam **85/167 (50,9%)**; incluindo ate `docs/**` (que a §4 PROIBE) chega a 89; com o maximo teorico (`plans+adr+qualquer *.md`) chega a 98. **Os 106 sao inalcancaveis** — o plano os herdou de uma classificacao por commit (137/243 commits sao docs-only pela mesma regra: 56%, contra 51% dos pushes). FATOR 2 — minutos. Medi os jobs de 4 runs verdes: matrix ~34 min wall (36 faturados com round-up por job), dual-rail ~7,7 (9), E2E 1,9 (2), formal 0,25 (1) => **48 min pesados por run, nao 65,4**. Compondo os dois: A1 real = 85 x 48 x 0,022 = US$ 89,8/21d = **US$ 4,28/dia**, contra a manchete de US$ 9,24/dia (base MEDIDA) — 54% de divergencia. O AC-6 (`>20% reabre o plano`) dispara por construcao no D+7, antes de qualquer efeito de execucao.

**Evidência.** `gh run list --workflow=validate.yml --limit 200 --json headSha,createdAt` (167 na janela, 167 heads unicos, 0 ausentes localmente) + `git diff --name-only <head[i-1]> <head[i]>` -> 85/167; `gh api /repos/Canhada-Labs/ceo-orchestration/actions/runs/32431818032/jobs` (steps por job); PLAN-184:83-86,105,199-202

**Cura proposta.** Reexpressar a §2 sobre os dois numeros medidos (85 pushes pulaveis; 48 min faturados de jobs pesados por run) antes do flip para `reviewed`, e reancorar o AC-6 nessa projecao. Se a decisao for manter a manchete ate a W0, entao o AC-6 tem de comparar contra a projecao POS-US1, nunca contra os US$ 224/21d atuais.

## Riscos — P1

### F-03 — A W0-US5 mede a grandeza errada: minutos por job nao decidem bucket, porque hoje TODO run roda TODOS os jobs

**Como falha.** O Check da US5 manda derivar `minutos por JOB por run` via `gh run view --json jobs` sobre os 167 runs para fechar o delta de +1.884 min (docs) contra -1.910 (codigo). Mas nao existe filtro hoje: cada run executa os mesmos 7 jobs, logo a distribuicao por job e aproximadamente identica nos dois buckets e a medicao volta sem informacao sobre a atribuicao. Rodei o instrumento em 4 runs verdes: as somas sao 64,8 / 60,5 / 64,0 / 65,3 min — constantes, e todas ~20% abaixo da media 80,4 do plano. A pergunta real da US5 ('quantos runs o filtro de fato pularia') so e respondida simulando o filtro sobre o diff do PUSH, que e outro comando e outro dado. Executar a US5 como escrita gasta a wave e devolve o delta intacto.

**Evidência.** PLAN-184:930-941 (W0-US5 e seu Check); PLAN-184:105-107 (os deltas); `gh api .../actions/runs/{32431818032,32417024117,32415219524,32323677058}/jobs` -> somas 64,8/60,5/64,0/65,3 min

**Cura proposta.** Trocar o instrumento da US5 (e o da US1) pela simulacao do filtro: ordenar os 167 runs por createdAt, tomar `git diff --name-only head[i-1] head[i]` como o diff do push, e contar quantos pushes casam INTEIRAMENTE a denylist candidata. Saida = numero de runs pulados por entrada da denylist, que e exatamente o insumo que a §2 precisa. O delta de minutos vira OQ (a hipotese sobrevivente e round-up de faturamento + runs cancelados, nao classificacao).

### F-04 — A A2 vale ~US$ 0,2/dia medidos, nao US$ 0,52 — e a previsao de que os dois jobs estouram o timeout esta errada por 19x num deles

**Como falha.** O plano dimensiona a A2 com `(3,4 + 4,7) = 8,1 min/run` e escreve na W0-US3 que 'com fator 2-3x ... os dois estouram' o teto. Medicao direta do run 32431818032: `Formal verification mutation harness` roda 00:13:22Z -> 00:13:37Z = **15 segundos** totais (o passo de pytest e 3s), contra teto de 10 min; `E2E integration tests` roda 00:14:49Z -> 00:16:32Z = **1m43s** (86s + 7s + 1s de pytest), contra teto de 8 min. Ou seja 2,15 min/run de wall (3 faturados com round-up), nao 8,1. Consequencia dupla: (i) a A2 marginal depois da A1 vale 3 x 82 pushes de codigo x 0,022 = US$ 5,4/21d = **US$ 0,26/dia**, e o plano dedica uma unidade [P0] de W0 (com rota de medicao, dimensionamento por pior caso e 3 runs verdes consecutivos) a um premio dessa ordem; (ii) mesmo a 3x, E2E vai a ~5,2 min contra teto 8 (racio 0,65) e formal a ~0,75 contra 10 — nenhum dos dois estoura, e o item [P0] de 'bump de timeout no MESMO commit' resolve um problema que a medicao nao mostra.

**Evidência.** `gh api /repos/Canhada-Labs/ceo-orchestration/actions/runs/32431818032/jobs` (steps com started_at/completed_at por job); PLAN-184:86,199-202,767-769; validate.yml:1079 (timeout 8), :1142 (timeout 10)

**Cura proposta.** Substituir 3,4/4,7 pelas duracoes medidas na §1 e na W0-US3, e reclassificar a W2: ou executa-la como item barato SEM wave de medicao propria (o teto atual ja cobre 3x), ou corta-la e registra-la como residuo. O ganho de rebaixar a W2 e liberar a W0 para o unico numero que decide o plano (F-02/F-03).

### F-05 — Nenhum backstop: o plano copia o filtro do coverage.yml e deixa para tras o `schedule:` que o torna sobrevivel

**Como falha.** A §1 registra que `coverage.yml` tem `schedule: 0 7 * * *`, e as Reference links (:1266) chegam a afirmar o contrario ('o gatilho dele e so `pull_request`'). Nenhuma das duas leituras vira decisao: o workflow novo da Rota C nasce com push+PR+dispatch e SEM cron. Sem cron, uma entrada de denylist que envelheca (um diretorio de codigo que passe a viver sob `.claude/plans/**` — ja existem **272 arquivos .py** la, incluindo arvores staged com hooks e testes) produz um silencio permanente: nenhum run, nenhum vermelho, nenhum sinal, ate alguem reparar por acaso. Com cron diario, o mesmo erro fica visivel em <=24h. O proprio repo ja registra o mecanismo em `ownership-nightly.yml:6-8`: 'schedule: events IGNORE paths: filters' — o cron atravessa a denylist por construcao. Custo do backstop: os 4 jobs pesados em `ubuntu-latest` = **US$ 0** (repo publico, verificado `visibility: public`), ou 48 min/dia no `Ceo` = US$ 1,06/dia se rodar no runner pago.

**Evidência.** .github/workflows/coverage.yml:15 (`cron: 0 7 * * *`); .github/workflows/ownership-nightly.yml:6-8; PLAN-184:56-59 vs PLAN-184:1266; `find .claude/plans -name '*.py' | wc -l` -> 272; `gh api repos/Canhada-Labs/ceo-orchestration --jq .visibility` -> public

**Cura proposta.** Adicionar `schedule:` (nightly) ao workflow novo, com os jobs pesados em `ubuntu-latest` no caminho agendado se o custo importar, e um AC que exija UM run agendado verde antes de fechar a W1. Corrigir a linha :1266 das Reference links, que contradiz a §1.

### F-06 — O custo de MANTER o filtro nao esta quantificado nem instrumentado — so o custo de UMA VEZ (as 4 superficies derivadas)

**Como falha.** O F10 precifica o custo pontual (CTO-GUIDE, badge, 2 ADRs, GOVERNANCE-MAP) e a §6 diz que 'esse custo e de documentacao, pago uma vez'. Mas a denylist e uma afirmacao sobre o repositorio que envelhece a cada commit: nenhum teste assere que as entradas continuam sem leitor nas 4 suites pesadas, nenhuma cadencia de re-derivacao, nenhum dono, nenhum gate. O proprio plano exibe a prova de que essa classe apodrece aqui: o F11 (validate.yml:736-739) e logica de deteccao de path, escrita por nos, morta na perna `pull_request`, com comentario citando um job inexistente — e ninguem viu porque nada mede. A prova de inercia da W0-US2 e um evento unico; no dia seguinte ao land ela ja e historia. Inputs -> consequencia concreta: alguem cria `.claude/plans/PLAN-190/staged/` com codigo que uma suite pesada passa a ler (ja ha 272 .py sob `.claude/plans/`), e a partir dai TODO commit que toque so aquele diretorio pula os 4 pesados com o alvo mudando por baixo.

**Evidência.** PLAN-184:588-599 (F10), PLAN-184:640-651 (§6 'pago uma vez'), PLAN-184:534-556 (F11); validate.yml:736-739; `find .claude/plans -name '*.py' | wc -l` -> 272

**Cura proposta.** Mecanizar a metade ESTATICA da US2 como teste em `.claude/scripts/tests/` (le a denylist do YAML do workflow novo, e falha se qualquer teste das 4 suites pesadas referenciar um caminho coberto por ela) — o teste roda no job de governanca, que nunca e filtrado. Somado ao cron do F-05, o custo recorrente vira dois numeros declarados em vez de zero implicito.

### F-07 — A alternativa de maior retorno por risco — reduzir a matriz de 4 versoes de Python no push — nunca e enumerada

**Como falha.** Medido, `hook-tests-python-matrix` consome ~34 min wall / ~36 min faturados dos ~48 min pesados por run: **75% do custo que a A1 ataca**. Rodar so as versoes de fronteira (3.9 e 3.12) no `push` e manter as 4 no PR e no nightly economiza ceil(7,7)+ceil(9,2)=18 min/run x 167 runs x 0,022 = US$ 66/21d = **US$ 3,15/dia** — a mesma ordem do premio real da A1 (US$ 4,28/dia, F-02) — sem filtro nenhum, sem classe de falso-verde, sem superficie derivada, sem cerimonia sobre um arquivo novo. E o risco e ESTRITAMENTE menor que o da A1, que ja aceita pular as quatro versoes inteiras em commits de docs. A §7 ('o que este plano NAO faz') recusa `-n auto` com razao escrita, mas nao menciona a reducao de matriz — logo a alternativa nunca foi pesada.

**Evidência.** validate.yml:1445-1477 (matrix 3.9/3.10/3.11/3.12); `gh api .../actions/runs/32431818032/jobs` -> legs 7,8/9,2/9,3/7,7 min; PLAN-184:690-707 (§7)

**Cura proposta.** Enumerar a reducao de matriz como opcao A0 na §2/§6, com o numero medido ao lado, e deixar o Owner escolher a ordem. Se ela entrar antes da A1, o premio residual da A1 encolhe e a decisao sobre gastar a cerimonia num workflow novo muda.

### F-08 — A premissa 'o Ceo e self-hosted, inventario de binarios desconhecido' que sustenta o AC-5 e falsa

**Como falha.** A W2 justifica o AC-5 ('delta de skip = 0') dizendo que `Ceo` e self-hosted e `ubuntu-latest` e 'outra imagem'. Verificado: `gh api /repos/Canhada-Labs/ceo-orchestration/actions/runners` devolve `total_count: 0` (nenhum runner self-hosted registrado), a org tem o grupo hospedado `Default Larger Runners` com `allows_public_repositories: true` (que e por que um repo publico e faturado), e os jobs reportam `runner_name: ceo-1000004236` com `labels: ['Ceo']` — larger runner HOSPEDADO, mesma familia de imagem. Consequencias: (i) o envelope '2-3x' importado do `ownership-nightly.yml:4-6` compara uma bateria LOCAL com um runner 2-core, nao 8-core hospedado com 2-core hospedado — para dois jobs SERIAIS a diferenca de nucleos quase nao pesa (o que pesa e checkout/pip, que sao de rede); (ii) o risco que o AC-5 mira (skips novos por binario ausente) e bem menor do que o texto afirma, embora o AC continue barato e valha manter.

**Evidência.** `gh api /repos/Canhada-Labs/ceo-orchestration/actions/runners` -> {"total_count":0}; `gh api /orgs/Canhada-Labs/actions/runner-groups` -> id 3 'Default Larger Runners' allows_public_repositories true; job JSON runner_name `ceo-1000004236`; PLAN-184:869-880 (W2 AC-5), PLAN-184:770-772 (fator 2-3x)

**Cura proposta.** Reescrever a premissa da W2 com o fato medido e manter o AC-5 pelo motivo certo (variacao de tool-cache/pip entre imagens), nao pelo motivo falso (self-hosted). Substituir o envelope 2-3x pelo racio medido/teto real (E2E 1,9/8 = 0,24; formal 0,25/10 = 0,025).

## Nice-to-have (advisory) — P2

### F-09 — O inventario de claims de substrato nao verificadas omite justamente as duas que decidem as rotas

**Como falha.** A §6 lista cinco claims nao verificadas (sem `paths` por job; grupo de concorrencia global; dispatch ignora filtro; dispatch e por ref; push filtrado nao cria run) e promete confirmar tres na W1. Faltam as duas load-bearing: (a) **'job skipped satisfaz um required check'** — e ela que faz a Rota B ser nomeada como 'a rota compativel com um futuro required-check' (F1) e sustenta a OQ-5; se for falsa, a rota de migracao nomeada nao existe e quem ligar branch protection descobre depois; (b) **'quando o GitHub nao consegue computar o diff, ele roda'** — o argumento inteiro de seguranca da Rota C recomendada, e nenhum Check da W1 o exercita. Verifiquei o estado que torna isso latente e nao agudo: `branches/main/protection` = 404, `rulesets` = [], `rules/branches/main` = [] — nao ha required check hoje. Some-se que a resposta padrao da industria para filtro + required check (um job companheiro que sempre roda e sempre passa, com o MESMO nome de check) nunca aparece no inventario de rotas do plano (so B e C).

**Evidência.** PLAN-184:668-700 (a lista de 5 claims); PLAN-184:470-486 (F1 e a ressalva durable); OQ-5 em PLAN-184:1104-1112; `gh api repos/Canhada-Labs/ceo-orchestration/branches/main/protection` -> 404; `gh api .../rulesets` -> []

**Cura proposta.** Acrescentar as duas claims a lista da §6 marcadas NAO-VERIFICADAS, e nomear a 'Rota D' (companion job always-success com o mesmo nome de check) na OQ-5 como a terceira opcao para o dia do required check — e mais barata que migrar C->B, que agora carrega o preco de `paths` x `concurrency`.

### F-10 — O plano nao precifica o proprio instrumento de aceite, que roda inteiro no runner pago por construcao

**Como falha.** AC-1 (plant + reversao), AC-2b (fronteira mista), AC-9 (PR) e o item [P0] da W2 ('tres runs verdes consecutivos') exigem pushes que tocam `.claude/hooks/**` ou `.github/workflows/**` — e `.github/workflows/**` e exclusao DURA da denylist (AC-4), logo cada um desses pushes dispara o conjunto pesado completo. Medido: 48 min pesados + 19 de governanca = ~67 min faturados = **US$ 1,47 por push de validacao**; sao ~8-10 pushes entre W1 e W2 => US$ 12-15, ou ~3 dias da economia real (US$ 4,28/dia, F-02). O plano precifica so a rota (b) da OQ-8 (US$ 1,59/run) e trata o resto do instrumento como gratis. Nao e bloqueante — e um numero que falta na mesma tabela que justifica o plano.

**Evidência.** PLAN-184:829-866 (controles A/B/C/D), PLAN-184:876-880 (3 runs verdes), PLAN-184:1121-1128 (OQ-8, unico custo precificado); `gh api .../actions/runs/32431818032/jobs` (48+19 min)

**Cura proposta.** Somar uma linha de 'custo do instrumento de aceite' a §2 (~US$ 12-15) e, onde der, usar `workflow_dispatch` do workflow novo em vez de push para os runs de validacao da W2 — dispatch nao dispara o job de governanca, cortando ~US$ 0,42 por run.

## What I would NOT change

- A recomendacao pela Rota C. Fui procurar o que quebraria no split e nao achei: os 7 jobs de validate.yml nao tem NENHUM `needs:` entre si, nenhum usa secrets, nenhum outro workflow tem `workflow_run` sobre validate.yml (o unico `workflow_run` do repo esta em npm-publish.yml e observa `release.yml`, nao validate), o release-gate enumera outros 6 workflows (`release.yml:551`) e nao validate, e nenhum script ou gate fixa os 4 job-ids ao arquivo — as unicas referencias sao 2 docstrings de teste e os 2 ADRs que o F10 ja manda atualizar. O split e mecanicamente limpo, e o achado de `paths` x `concurrency` contra a Rota B esta correto.
- A doutrina denylist-sobre-allowlist da §3 e a correcao do mecanismo na §4. `validate_file_ref` (test_threat_model_coverage.py:199-215) e mesmo um detector de EXISTENCIA com fallback de prefixo, e exigir MUTAR+RENOMEAR+APAGAR com o Check pedindo o VERMELHO e a unica prova que fecha aquele buraco. Manter `docs/**` e `.github/**` fora da denylist esta certo.
- A analise de cobertura residual da §4, que e o que torna a A1 aceitavel, confere linha a linha: o job de governanca nao filtrado roda `.claude/hooks/tests/` (validate.yml:334-341), `.claude/scripts/tests/` + optimizer (:419-425) e mais dez raizes incluindo `tests/unit`, `_lib/tests`, swarm, replay, federation, mcp-server, detectors, predict-budget, forensic, synthetic (:440-466), tudo em Python 3.12 com `-n auto`. O que um commit so-docs perde e exatamente (i) 3.9/3.10/3.11, (ii) as duas pernas CEO_NATIVE_SUBAGENTS e (iii) integration/formal/tier_policy/tournament — como escrito.
- A recusa de `-n auto` nos dois jobs seriais (§7) e o tratamento da rota de recuperacao: que `workflow_dispatch` despacha em REF e nao em SHA, que sob a Rota C 're-run' e vacuo porque nao existe run, e que sob a Rota B o re-run REAVALIA o `if:` e pula de novo — os tres estao certos e sao a parte que quase todo plano de filtro erra. Verifiquei tambem que nao ha git hook local (.git/hooks vazio), entao o plant do AC-1 nao encontra bloqueio mecanico no push.

## Cobertura declarada

Li o plano inteiro (1293 linhas) e verifiquei contra o disco: validate.yml (on:, concurrency, permissions, os 7 jobs, os 4 corpos pesados), coverage.yml, ownership-nightly.yml, release.yml (release-gate), npm-publish.yml (workflow_run), check_canonical_edit.py, verify-counts.sh, CTO-GUIDE.md:46, README.md:8, as suites pesadas (rglob/_REPO_ROOT). Medi com a API: os 167 runs da janela (F2 confere exatamente: 167 push/main, 79 cancelled/57 success/31 failure), a simulacao do filtro sobre o diff de PUSH entre heads consecutivos (85/167 pulaveis), duracoes por job de 4 runs verdes, ausencia de branch protection/rulesets, e o tipo do runner Ceo. NAO consegui verificar (sem experimento vivo, e fora do meu eixo): (i) se um job `skipped` satisfaz required check — nao ha protection configurada para testar; (ii) o comportamento de paths-ignore quando o GitHub nao computa o diff (force-push, >1000 commits); (iii) semantica de merge_group — nao ha merge queue no repo; (iv) o arredondamento exato de faturamento por job em larger runners: usei ceil(min) por job, entao meus dolares tem incerteza de ~1 min/job; (v) minha amostra de duracao e de 4 runs VERDES — runs cancelados (47% da janela) podem faturar diferente e explicam parte do gap entre os 63,7 min medidos e os 80,4 min/run da media do plano. Nao cobri seguranca nem estatistica por instrucao.
