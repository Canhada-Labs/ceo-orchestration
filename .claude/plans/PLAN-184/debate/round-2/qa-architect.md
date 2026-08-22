# Crítica — Principal QA Architect

> Rodada 2 do debate do PLAN-184. Rótulo anonimizado na síntese: **Critic-C**
> (mapa em `anonymization-map.md`). Eixo desta crítica: medicao, aritmetica e instrumento de aceite: reproducao dos numeros, ACs que podem falhar.
> Agente read-only (ADR-136-AMEND-1): não editou arquivo nenhum;
> toda claim foi verificada contra o disco antes de entrar aqui.

## Verdict

**ADJUST_PROCEED**

## Summary (≤ 3 bullets)

- A cifra que autoriza o plano NAO reproduz. O billing real (endpoint novo, que funciona) diz 8.789,9 min de 8-core no repo em 08-01..08-21 = US$ 193,38; o plano declara 14.291 min = US$ 314,40. Reconciliei dia a dia: o metodo de medicao do plano bate com a fatura em 20 dos 21 dias (erro <3%) e estoura em UM: 2026-08-21, medido 5.408 min vs FATURADO 231,9 — o dia em que o teto disparou e matou jobs que nunca foram cobrados. O plano conta esse tempo morto como 'custo bruto' e depois chama a diferenca de 'trabalho que nao rodou'; o sinal esta invertido.
- Removido o artefato, a manchete cai de 77,7% para 58,8% e o teto REAL da A1 e US$ 4,04/dia contra os US$ 9,24/dia projetados (2,3x). Pior: a projecao combinada A1+A2 (US$ 10,67/dia) e MAIOR que o gasto total medido do workflow que ela corta (US$ 8,91/dia) — impossivel por construcao. E a §2 afirma que os 77,7% 'sobrevivem as duas bases': na base TABELA o custo/run e constante, logo a fracao e 106/167 = 63,5%, nunca 77,7%.
- A W3 nao tem instrumento. O endpoint classico de billing devolve HTTP 410; o que funciona nao tem dimensao de WORKFLOW e mistura 4 repos da org. E o gate '>20% reabre' e mais estreito que o ruido do proprio indicador: janelas de 7 dias na linha de base variam de US$ 4,95 a US$ 14,64/dia (2,96x, +-49%) sem nenhuma intervencao. O AC-6 fica VERMELHO por volume de commit, nao pelo filtro.

## Must-fix (blocking) — P0

### QA-01 — Os 14.291 min / US$ 314,40 da §1 nao reproduzem: ~5.176 min sao tempo morto do dia do teto, nunca faturado

**Como falha.** O plano (§1, linhas 25-37) poe na MESMA tabela 'Custo bruto US$ 314,40' e 'Faturado de fato US$ 200' e conclui que a diferenca 'nao e economia, e trabalho que nao rodou'. Reconciliei dia a dia contra a fatura: somando duracao de job (teto por job, runner label 'Ceo'), o metodo bate com o billing em 20 dos 21 dias (ex.: 08-18 medido 1.452 vs faturado 1.465; 08-13 936 vs 946; 08-04 883 vs 901). Em 2026-08-21 medido = 5.408 min, FATURADO = 231,9 min — excesso de 5.176 min. Esse dia e o teto disparando: jobs cronometram start..complete atravessando a morte por budget e nao geram cobranca. Consequencia concreta: o Owner autoriza o corte olhando um problema de US$ 14,97/dia quando o gasto real e US$ 9,21/dia (repo, 8-core, 21 dias), e o excedente que ele acha ser 'demanda reprimida a 0,022/min' e tempo que jamais foi faturavel. O sinal do argumento esta invertido.

**Evidência.** gh api "/organizations/Canhada-Labs/settings/billing/usage?year=2026&month=8" -> sku 'Actions Linux 8-core', repositoryName 'ceo-orchestration': 8.811,909 min no mes, 8.789,9 em 08-01..08-21 (US$ 193,38); org-wide 9.213,9 (US$ 202,71). Serie diaria vs medido em .../actions/runs/{id}/jobs (started_at..completed_at, ceil): divergencia isolada em 2026-08-21 (5.408 vs 231,9). Plano: .claude/plans/PLAN-184-ci-cost-routing.md:27-37

**Cura proposta.** Reescrever a §1 sobre a janela LIMPA 08-01..08-20 e declarar o dia 08-21 como excluido, com a razao. Todo numero de custo passa a vir do endpoint que existe (/organizations/{org}/settings/billing/usage), com o comando ao lado. O par 'gross vs faturado' sai da tabela: para larger runners gross == net (disc=0,00 no proprio payload), logo nao existe um 'bruto de US$ 314,40' em lugar nenhum.

### QA-02 — A projecao de corte (US$ 10,67/dia) e MAIOR que o gasto total medido do workflow que ela corta (US$ 8,91/dia)

**Como falha.** §2:183-187 declara 'US$ 224 na janela de 21 dias = US$ 10,67/dia de corte (71%); custo residual US$ 90/21d = US$ 4,29/dia' — total implicito US$ 14,96/dia. Medi o validate.yml no runner pago na janela limpa (08-01..08-20): 8.096 min = US$ 178,11 = US$ 8,91/dia, TUDO incluido (governanca + 4 pesados + pushes de codigo). Um corte de US$ 10,67/dia sobre uma base de US$ 8,91/dia e aritmeticamente impossivel. Decompondo, o teto REAL da A1 (os 4 pesados rodando em pushes so-docs, que e exatamente o que o filtro elimina) e 3.672 min = US$ 80,78 = US$ 4,04/dia — contra os US$ 9,24/dia que a §2 atribui a A1 na base MEDIDA (fator 2,29x). Consequencia: a W3 vai comparar a fatura contra uma projecao que nenhum filtro poderia atingir, o AC-6 vai medir divergencia de ~60% e 'reabrir o plano' por um defeito da projecao, nao da execucao.

**Evidência.** Derivacao: para cada um dos 167 runs de validate.yml na janela, gh api /repos/Canhada-Labs/ceo-orchestration/actions/runs/{id}/jobs?per_page=100, filtrando labels[0]=='Ceo', ceil(started_at..completed_at), started_at[:10] <= 2026-08-20, cruzado com a classificacao do push (git log prev_head..head --name-only). Resultado: docs/HEAVY=3.672 min (US$ 4,04/dia), docs/GOV=1.090, code/HEAVY=2.579, code/GOV=755; total 8.096 min. Plano: PLAN-184:172-187 e 1078-1081 (OQ-2)

**Cura proposta.** Substituir A1/A2/residual pelos quatro numeros derivados acima (docs/HEAVY, docs/GOV, code/HEAVY, code/GOV) e declarar A1 = docs/HEAVY = US$ 4,04/dia como TETO, nao como esperado. Acrescentar um piso de decisao explicito na W0: 'se o teto da A1 ficar abaixo de US$ X/dia, o plano nao se paga e nao executa' — hoje nao existe nenhum valor abaixo do qual o plano seria abandonado.

### QA-03 — A manchete de 77,7% e artefato do dia do teto e NAO sobrevive as duas bases, ao contrario do que a §2 afirma

**Como falha.** §2:162-164 diz: 'O que sobrevive as duas bases, e e o que autoriza o plano: [...] 77,7% do custo cai em commits que nao tocam codigo', e a sintese repete (synthesis.md:46-49). Duas falhas independentes. (a) Na base TABELA todo run custa os mesmos 80,4 min por construcao, logo a fracao de custo so-docs E a fracao de RUNS: 106/167 = 63,5%. O numero 77,7% nao existe nessa base — ele so aparece na base MEDIDA, que e justamente a que a W0-US5 declara NAO-DERIVADA. A frase afirma sobrevivencia de um numero que so uma das bases produz. (b) Medindo de verdade: com o dia 08-21 dentro, a fracao so-docs e 74,2%; removido o artefato de teto, cai para 58,8% — e o resultado e estavel em duas definicoes de 'docs' (com e sem .claude/skills/). Ou seja, 5.256 dos 5.408 minutos medidos em 08-21 (97%) caem no bucket docs e NENHUM deles foi cobrado: um unico dia nao-faturado fornece a manchete. Consequencia: o Owner flipa para 'reviewed' acreditando que 4 em cada 5 dolares vem de markdown, quando sao ~3 em 5.

**Evidência.** Sensibilidade rodada em 3 variantes de classificador x 2 cortes de janela: variantes A (.md+plans+adr+docs/+skills/) e B (.md+plans+adr+docs/) dao 74,2% COM 08-21 e 58,8% SEM. Denominador tambem indeclarado: 228,95/(228,95+65,87)=77,66% e sobre o custo do validate.yml; sobre os 14.291 min do runner pago seria 72,8%. Plano: PLAN-184:56-58, 75-77, 162-164; synthesis.md:46-49

**Cura proposta.** Trocar a manchete por '58,8% do custo do validate.yml no runner pago cai em pushes que nao tocam codigo (janela limpa 08-01..08-20)', com o denominador nomeado na propria frase. Apagar a afirmacao de que 77,7% sobrevive as duas bases — na base TABELA a fracao e mecanicamente 106/167.

### QA-04 — A W3 nao tem instrumento: o endpoint que o plano congelaria esta morto (410), o que funciona nao tem dimensao de workflow, e o gate de 20% e mais estreito que o ruido

**Como falha.** AC-6 (linha 1048) e o Check da W3 (linha 986) exigem 'o comando de billing citado' e disparam reabertura acima de 20% de divergencia. Tres defeitos que se somam. (a) O endpoint classico responde HTTP 410 'This endpoint has been moved' — a W0-US4 congelaria um comando que ja nao existe. (b) O endpoint vivo tem eixos product/sku/date/repositoryName e NENHUM eixo de workflow: nao ha como atribuir a variacao ao validate.yml, e a mesma fatura carrega arbitrage-monitor, 42ledger-core e ceo-orchestration-private. (c) O gate: medi janelas moveis de 7 dias na propria linha de base, mesmo repo, mesma configuracao, ZERO intervencao — US$ 4,95/dia (janela iniciando 08-01) ate US$ 14,64/dia (08-13), razao 2,96x, +-49% em torno do centro. O AC-6 usa +-20%. Consequencia concreta: qualquer que seja o efeito do filtro, a W3 fecha com divergencia acima de 20% e 'reabre o plano' — o instrumento pode ficar vermelho, mas o vermelho mede volume de commit, nao o corte. E se por acaso ficar verde, tambem nao prova nada.

**Evidência.** gh api /orgs/Canhada-Labs/settings/billing/actions -> {"message":"This endpoint has been moved.","status":"410"}. gh api "/organizations/Canhada-Labs/settings/billing/usage?year=2026&month=8" -> chaves ['date','discountAmount','grossAmount','netAmount','organizationName','pricePerUnit','product','quantity','repositoryName','sku','unitType'] (sem workflow). Janelas de 7d, repo ceo-orchestration, 8-core: min 1.576 min / max 4.658 min. Plano: PLAN-184:810-820 (W0-US4), 979-993 (W3), 1048-1052 (AC-6)

**Cura proposta.** Congelar na W0-US4 o endpoint que existe E um normalizador de atividade: o numero que fecha o AC-6 passa a ser US$ por PUSH (ou por run de validate.yml), nao US$/dia-calendario. Melhor ainda, e derivavel do mesmo dado: comparar o custo MEDIO de um push so-docs antes (medido: 4.762/93 = 51,2 min) contra depois — esse par e imune a variacao de volume. Guardar US$/dia apenas como leitura de caixa, nunca como o numero que dispara o gate.

## Riscos — P1

### QA-05 — A W0-US5 pre-registra a hipotese errada: o delta de +-1.884 min e variancia de duracao, nao erro de classificacao

**Como falha.** §1:113-121 e a W0-US5 (821-832) afirmam que os deltas quase simetricos '+1.884,6 / -1.910,4' indicam 'redistribuicao' e mandam testar primeiro 'erro de classificacao de ~23-24 runs'. O calculo que produz esses deltas multiplica a MEDIA GLOBAL (80,4 min/run) pela contagem de cada bucket — o que so e valido se os buckets forem homogeneos. Medi: runs de push so-docs custam 99,4-102,2 min em media; runs de push com codigo custam 50,5-51,0. Os buckets diferem por ~2x, logo mean x count e invalido e o residual e exatamente o esperado, sem nenhuma reclassificacao. Testando a hipotese do plano diretamente: reclassificando pelo PUSH INTEIRO (o que o filtro ve) em vez do commit-ponta, apenas 5 runs mudam de bucket — nao 23-24. Consequencia: a W0-US5 gasta a wave inteira caçando um fantasma e o Check ('delta residual abaixo de 5% OU a causa nomeada') sera fechado com a causa errada nomeada, congelando um numero que continua errado por outro motivo (o do QA-01).

**Evidência.** Medicao por bucket (167 runs, ceil por job, label Ceo): POR PUSH docs n=98 min=10.018 media=102,2 | code n=69 min=3.486 media=50,5. POR HEAD_SHA docs n=103 media=99,4 | code n=64 media=51,0. Runs que trocam de bucket ao usar o push inteiro: 5 (runIds 31223529242, 31492701458, 31710266051, 32319365891, 32491751097). Por conclusao: cancelled n=79 media=99,0 | success n=57 media=66,3. Plano: PLAN-184:104-123, 821-832

**Cura proposta.** Reescrever a nota de reconciliacao: o residual e variancia entre buckets (docs ~2x mais caro por run, porque acumula runs cancelados longos), nao redistribuicao. A W0-US5 muda de objetivo — em vez de 'achar 23 runs mal classificados', ela publica media e desvio POR BUCKET e usa a soma real por bucket, que ja e o numero certo. Isso tambem elimina a marcacao NAO-DERIVADA e destrava a OQ-6 sem gate.

### QA-06 — A unidade e o PUSH, nao o commit — a atribuicao e os controles positivos estao na granularidade errada

**Como falha.** Toda a §1 classifica COMMITS (236 commits, 153 so-docs; censo do debate: 239 = 152+67+20) e o AC-2b (1025-1030) especifica 'um UNICO commit tocando .claude/plans/** e um arquivo sob .claude/hooks/**'. Mas o gatilho e push em main (F2: 167/167) e o filtro do substrato avalia a UNIAO dos arquivos de TODOS os commits do push. Medi: 21 dos 167 pushes carregaram mais de um commit, com maximo de 21 commits em um unico push, e 242 commits chegaram por 167 pushes. O caso perigoso e o push MISTO POR COMMITS — um commit de docs e um de codigo empurrados juntos — e ele nao e exercitado por nenhum AC: o AC-2b so testa mistura DENTRO de um commit. No ramo B isso e a diferenca entre diffar 'github.event.before...github.sha' (correto) e 'HEAD~1..HEAD' (silenciosamente errado), e o molde in-repo que a §6 manda copiar (shadow-ci.yml:65-75) e justamente um diff de duas pontas. Consequencia: um detector que passe em AC-1, AC-2 e AC-2b ainda pula os 4 pesados num push que contem codigo, e o repo tem 21 desses na janela.

**Evidência.** Derivado de gh run list --workflow=validate.yml (167 runs, ordenados por createdAt) + git log prev_head..head --no-merges --name-only entre runs consecutivos: pushes com >1 commit = 21, max 21 commits/push, total 242 commits. Classificacao por head_sha {docs:103, code:64} vs por push {docs:98, code:69}. Plano: PLAN-184:68-73 (censo em commits), 1025-1030 (AC-2b), 576-577 (molde shadow-ci)

**Cura proposta.** Trocar 'commit' por 'push' em toda a §1 e nos ACs, e acrescentar um AC-2c: um unico PUSH contendo dois commits (um so-docs, um tocando .claude/hooks/**) tem de executar os 4 pesados, provado por gh run view --json jobs. No ramo B, o Check passa a exigir literalmente o par github.event.before...github.sha na expressao, com o caso de before zerado caindo em 'roda tudo'.

### QA-07 — A W0 nao nomeia o resultado que mata a manchete, e a OQ-6 agenda a medicao letal em paralelo a edicao irreversivel

**Como falha.** A tarefa da W0 e 'medir e derivar antes de filtrar', mas nenhum dos cinco Checks nomeia um resultado que interrompe o plano. O Check da US5 (832) pede so 'a §2 registra qual das duas bases sobreviveu' — as duas bases sao aceitaveis por construcao. O Check da US1 (739) pede a lista publicada 'com a soma das fracoes declarada' — nenhuma fracao minima. E a OQ-6 (1106-1115) recomenda explicitamente a opcao (a): a W1 abre com 'a direcao' enquanto a US5 roda em paralelo. Isso torna a W0 um pre-registro sem hipotese nula: qualquer numero que ela produzir e compativel com prosseguir. Com o numero real na mesa (teto de A1 = US$ 4,04/dia contra US$ 9,24/dia projetado, QA-02), esse era exatamente o resultado que deveria ter parado o plano na W0, e nao ha clausula que o faca. Consequencia: as quatro superficies derivadas, o split de workflow e as edicoes de ADR do W1 acontecem antes de existir um numero que justifique o trabalho.

**Evidência.** PLAN-184:725-739 (W0 abertura + Check US1), :832 (Check US5), :1106-1115 (OQ-6, recomendacao (a)), :1230-1236 ('How to continue': 'A US5 (reconciliacao) roda em paralelo'). Nenhuma ocorrencia de limiar de abandono: grep por 'nao executa', 'abandona', 'piso' na secao Waves nao devolve clausula de parada.

**Cura proposta.** Acrescentar a W0 um item [P0] de pre-registro com o resultado que mata: 'se o teto da A1 derivado na US5 ficar abaixo de US$ N/dia, ou se a fracao de custo so-docs ficar abaixo de M%, a W1 nao abre'. Com os numeros medidos aqui (US$ 4,04/dia, 58,8%) o Owner decide N e M antes de ver o resultado, nao depois. E inverter a OQ-6: a US5 e barata (gh api sobre 167 runs, minutos) e ja esta feita — nao ha razao para paralelizar.

### QA-08 — O AC-5 ('delta de passed = 0') bloqueia o flip quando a cobertura MELHORA, e compara duas arvores diferentes

**Como falha.** AC-5 (1043-1046) e o Check da W2 (971) exigem colar a linha-resumo do pytest 'do ULTIMO run em Ceo e do PRIMEIRO run em ubuntu-latest', com 'delta de skipped = 0 e delta de passed = 0; delta nao-zero BLOQUEIA o flip'. Dois defeitos. (a) O delta nao e assinado: os pontos de skip citados sao gates de ambiente por shutil.which. Se a imagem ubuntu-latest tiver um binario que o larger runner nao tem, skipped CAI e passed SOBE — mais cobertura, nao menos — e o AC bloqueia o flip por ter melhorado. A direcao perigosa e apenas uma: skipped subindo. (b) Os dois runs sao de COMMITS diferentes (o ultimo push em Ceo e o push do flip), logo o conjunto de testes pode legitimamente diferir; nada no Check pina o SHA. Consequencia: a W2 fecha com um bloqueio espurio, ou — pior — alguem 'conserta' o AC afrouxando-o e perde o unico controle contra SKIP silencioso.

**Evidência.** PLAN-184:960-971 (Check W2) e :1043-1046 (AC-5). Sitios verificados no disco: tests/integration/test_install_sh_rollback.py:76-81 (_resolve_binary: shutil.which -> pytest.skip) e tests/integration/test_live_adapter_smoke.py:62-68 (skips por env flag e credencial, nao por binario — ou seja, a citacao do plano mistura dois mecanismos diferentes).

**Cura proposta.** Assinar o criterio: 'skipped(ubuntu-latest) <= skipped(Ceo) E passed(ubuntu-latest) >= passed(Ceo)'; qualquer teste que passe a SER PULADO bloqueia, teste que passe a RODAR nao bloqueia. E pinar a comparacao no mesmo SHA — rodar os dois jobs no mesmo commit (o proprio commit de flip, com um run de dispatch no runner antigo) em vez de comparar pushes vizinhos.

### QA-09 — A tabela que decide o plano nao fecha por 27 min, nao cita comando algum, e mistura pelo menos duas fontes sem coluna de fonte

**Como falha.** A §1 declara 'fonte unica de verdade; este plano nao os recalcula' (:22-23) e em seguida apresenta seis numeros sem um unico comando ao lado — enquanto a §5 (F1..F11) cita comando para cada fato. A licao registrada do proprio repo e 'medicao que sustenta decisao imprime seus INPUTS'. Alem disso a tabela nao fecha: 10.407 + 2.994 = 13.401, contra os 13.428 declarados para o validate.yml na tabela imediatamente acima — 27 min orfaos que nenhum bucket reclama e que nenhum Check da W0-US5 cobre (o Check fala do delta contra a tabela por-JOB, nao desse). E ha evidencia de fontes mistas: a linha '3.124 min em ubuntu-latest' fica a 2% do billing (3.052 min no mes), enquanto a linha '14.291 min no runner pago' fica 55% acima do billing (8.789,9) — ou seja, o autor teve acesso ao billing para uma linha da tabela e nao para a outra. Consequencia: nenhum leitor consegue recalcular a decisao, que e exatamente o que o plano precisa que o Owner faca antes do flip para reviewed.

**Evidência.** sed -n '19,99p' PLAN-184-ci-cost-routing.md | grep '^\$' -> vazio (nenhum comando na §1; a §5 tem varios). Aritmetica: 10.407+2.994=13.401 vs 13.428 (:44,:58-59). Billing free-runner ceo-orchestration agosto = 3.052 min vs 3.124 declarado (:30); 8-core = 8.789,9 vs 14.291 declarado (:27).

**Cura proposta.** Dar a §1 uma coluna FONTE e um comando por linha, no mesmo padrao da §5. Os comandos existem e estao neste relatorio: billing por sku/repo/dia via /organizations/{org}/settings/billing/usage, minutos por job via /repos/{o}/{r}/actions/runs/{id}/jobs, classificacao de push via git log prev..head --name-only. Fechar ou nomear os 27 min.

## Nice-to-have (advisory) — P2

### QA-10 — O AC-3 nao tem janela definida — nenhum comando pode falha-lo na forma como esta escrito

**Como falha.** AC-3 (1031-1033) exige que o job de governanca execute em '100% dos commits da janela de validacao'. 'Janela de validacao' nao e definida em lugar nenhum do plano — nao ha data, nem contagem de commits, nem criterio de encerramento. O unico Check mecanico correspondente (W1, :912-914) verifica UM run: o commit so-plans do controle B. Um AC universal ('100% dos commits') sustentado por uma amostra de tamanho 1 nao pode ficar vermelho por nada que nao seja aquele run especifico. Consequencia pratica: se o split introduzir uma condicao que pule a governanca em algum subconjunto de commits (por exemplo um paths-ignore copiado por engano para o validate.yml no mesmo commit), o AC-3 fecha verde.

**Evidência.** PLAN-184:1031-1033 (AC-3) e :912-914 (unico Check correspondente, sobre o run do controle B). Nenhuma definicao de 'janela de validacao' no arquivo.

**Cura proposta.** Definir a janela por comando: 'nos N primeiros pushes em main apos o commit de split, gh run list --workflow=validate.yml --json databaseId + gh run view --json jobs mostra o job de governanca presente em N/N'. Com N declarado (10 e barato: governanca ~14,6 min/run em ubuntu... nao, ela fica no Ceo, ~US$ 0,32/run, entao N=10 custa US$ 3,2).

### QA-11 — A 'assinatura aritmetica' dos 9090,909090 min e uma tautologia e nao casa com nenhuma quantidade medida

**Como falha.** §1:32-35 apresenta como corroboracao: 'a quantidade faturada — 9090,909090 min — e exatamente 200 / 0,022'. Dividir o teto pelo preco devolve necessariamente teto/preco: a identidade nao carrega informacao sobre o mundo, e esta escrita como se fosse uma medicao que confirma a outra. Pior, ela nao bate com o dado: o billing devolve 9.213,909 min de 8-core na org em 08-01..08-21 e 9.254,909 no mes ate 08-22, com grossAmount US$ 203,61 e discountAmount 0,00 (larger runners nao recebem minutos gratuitos). Nenhum desses e 9.090,909. O que de fato existe e uma fracao .909 no ultimo dia — assinatura de corte no meio de um minuto — mas o total ultrapassa o teto em ~123 min. Consequencia: um leitor que confie nessa linha acredita que a fatura foi verificada contra o teto quando nao foi.

**Evidência.** gh api "/organizations/Canhada-Labs/settings/billing/usage?year=2026&month=8": soma de quantity para sku 'Actions Linux 8-core' = 9.254,909 min (mes), 9.213,909 (ate 08-21); grossAmount 203,61; discountAmount 0,00; pricePerUnit 0,022 confirmado (8.811,909 x 0,022 = 193,86). Plano: PLAN-184:32-37

**Cura proposta.** Remover a linha ou substitui-la pelo dado real: 'o teto de US$ 200 foi atingido em 2026-08-21; a fracao de minuto (.909) no ultimo dia e a assinatura do corte; o consumo total do mes ficou em US$ 203,61 gross'. E deixar explicito que gross == net para larger runners, o que elimina a leitura de que existiu um bruto de US$ 314,40.

### QA-12 — A lista de Open questions esta corrompida na numeracao e a OQ-3 ainda carrega o rotulo '/mes' que a W0-US4 proibiu

**Como falha.** O flip para reviewed depende explicitamente das OQ-6..OQ-10 (:1216-1218, :1226-1228), logo a lista e load-bearing para a decisao do Owner. A sequencia impressa e 1, 2, 3, 4, 3b, 5 e depois 6..10 apos uma regra horizontal — o item '3b' aparece DEPOIS do 4, e ha duas entradas concorrentes para o mesmo residuo: a OQ-3 (:1082-1084) diz '~US$ 35/mes' e a OQ-3b (:1089-1091) reexpressa 'US$ 34,98 na janela de 21 dias = US$ 1,67/dia (leitura de 30 dias: US$ 50)'. O rotulo '/mes' da OQ-3 e exatamente a unidade que a W0-US4 congelou fora, e ele sobreviveu na lista que decide o flip. Consequencia: o Owner le duas versoes do mesmo residuo em duas bases diferentes e nao ha qual delas responde a pergunta.

**Evidência.** PLAN-184:1073-1098 (numeracao 1,2,3,4,3b,5) e :1102-1138 (6..10 apos '---'); OQ-3 em :1082 ('~US$ 35/mes') vs OQ-3b em :1089-1091. Regra congelada em :143-147 (W0-US4).

**Cura proposta.** Renumerar 1..10 em bloco unico e apagar a OQ-3, mantendo so a OQ-3b. Enquanto isso, corrigir tambem o numero: medi o residuo real da governanca sobre pushes so-docs na janela limpa em 1.090 min = US$ 23,98 = US$ 1,20/dia, nao US$ 1,67/dia.

## What I would NOT change

- A doutrina denylist-sobre-allowlist da §3 e a exclusao dura de docs/** e .github/** (AC-4). O argumento sobre direcao de falha esta certo e o contraexemplo da §4 e real: verifiquei validate_file_ref em tests/integration/test_threat_model_coverage.py:199-215 — e existencia (is_file/is_dir) com fallback de prefixo por startswith, sem leitura de conteudo. Nao trocar por allowlist para 'ficar igual aos outros 13 workflows'.
- A W0-US2(b) exigindo MUTAR + RENOMEAR + APAGAR com o Check pedindo o VERMELHO. E o unico instrumento do plano cujo criterio de aceite e um vermelho em vez de um verde, e e precisamente por isso que ele detecta o modo de falha que o repo chama de 'guard verde porque nao ve o alvo'. Nao relaxar para 'verde nas tres'.
- A bateria de controles positivos AC-1/AC-2/AC-2b, incluindo o plant que so quebra em Python 3.9. Custa CI pago (estimo ~US$ 8-13 no total, contra um ganho real de ~US$ 4/dia — payback de 2 a 3 dias) e vale cada centavo: e a unica prova comportamental de que o roteamento funciona. Nao cortar ACs para economizar minutos.
- A recusa de -n auto nos dois jobs seriais (§7) e a honestidade da §9 (residuo declarado com numero). Sao as duas decisoes que impedem o plano de virar outro plano e de vender '71%' sem dizer o que sobra.

## Cobertura declarada

COBERTURA. Critiquei apenas medicao/aritmetica/instrumento de aceite; nao avaliei pipeline (Rota B vs C, YAML, concorrencia) nem seguranca (permissions/F7). Reproduzi contra a API real: F2 bate exatamente (167 runs, 100% push em main, 79 cancelled/57 success/31 failure). O /timing devolve 0 ms para os 167 runs (so reporta 'UBUNTU'), entao NAO existe atribuicao de custo por workflow em nenhuma API — as unicas rotas sao (a) billing por sku/repo/dia e (b) soma de duracao de job. Validei (b) contra (a) dia a dia: erro <3% em 20 dos 21 dias, o que torna a divergencia de 08-21 um achado e nao ruido de metodo.

INPUT DA SINTESE R1 — O QUE FICOU PENDURADO (input para o round-2):
1. UM CRITICO INTEIRO NAO CHEGOU. A sintese declara '16 itens, 2 rotulos' (synthesis.md:20-35) e o indice de memoria do repo registra que o .slice() cortou 7 de 23 achados e um critico inteiro. O veredito ADJUST_PROCEED do r1 foi emitido sobre ~70% do material. Os 7 achados perdidos nao sao recuperaveis da sintese — so re-executando aquele critico (barato via resumeFromRunId).
2. C1 (P2) e RECONSTRUIDO, nao lido. O ultimo item do Critic-B corta em 'E "re-run" e'; a parte faltante foi reconstruida por verificacao independente (grep workflow_dispatch, coverage.yml:18). O que o critico disse APOS essa frase e desconhecido. A metade recuperada esta ancorada em disco e converge com o P2 do Critic-A, mas o item nao pode ser marcado como coberto.
3. P5 (contagem de skips) ficou meio-resolvido. A sintese corrigiu '8 pontos de skip' para '3 call sites + 6 sondas shutil.which'. Verifiquei no disco: test_install_sh_rollback.py:76-81 e um HELPER (_resolve_binary), nao um teste — o numero de TESTES que pulam continua sem medicao, e test_live_adapter_smoke.py:62-68 pula por env flag/credencial, nao por binario. O dimensionamento do S8/AC-5 segue sem base.
4. F11 segue NAO-VERIFICADA e nao fecha aqui: o tipo de github.event.pull_request.changed_files exige um payload de PR real, e este repositorio tem ZERO PRs em toda a sua historia (gh api /repos/.../pulls?state=all -> 0). Isso reforca o AC-9 e acrescenta um fato que o plano nao registra: o AC-9 criaria o PRIMEIRO PR da historia do repo, e esse PR dispara validate.yml (pull_request sem filtro de branch) no runner pago — custo nao orcado em lugar nenhum.
5. O achado S2 do r1 (P0 'a manchete nao e derivavel') foi ACEITO com o diagnostico errado; QA-05 mostra por medicao que a causa e variancia entre buckets. A sintese do r2 deve registrar S2 como CONFIRMADO-COM-CAUSA-TROCADA, nao como pendente.
6. A sintese declara em :46-49 que os 77,7% sobrevivem as duas bases; QA-03 falsifica. Esse e o unico ponto em que a sintese r1 introduziu uma claim que o plano nao tinha, e ela virou a frase que autoriza o plano.

LIMITE: nao consegui reconstruir de onde saiu o numero 14.291 min (nenhum metodo que testei o produz); trato-o como nao-reproduzivel, nao como falsificado.
