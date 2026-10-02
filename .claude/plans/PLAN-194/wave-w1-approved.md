# wave-w1-approved — sentinel da W1 do PLAN-194 (CI pronto para o Ubuntu 26.04)

> Assinatura e land em um passo: `bash .claude/plans/PLAN-194/wave-w1/OWNER-W1-SIGN.sh`
> (confere as pré-condições e o último registro do rail, confere que a cópia staged é o pós-imagem
> do patch e que o controle da W1 reprova no HEAD, aplica o patch, confere que os bytes aplicados
> são os revisados, roda a bateria — o controle da W1, o actionlint nas duas formas do CI, os gates
> de corpus e as suítes do `pytest.ini` com a divisão de marcadores do CI —, preenche Anchor-SHA,
> Patch-sha256, Rail-Record-sha256 e Data numa cópia do sentinel do HEAD, assina com a chave do
> allowlist de signatários, stageia o conjunto EXATO e commita; `--dry-run` ensaia sem assinar nem
> commitar). Push é decisão sua.

Plan: PLAN-194
Wave: W1 — CI pronto para o Ubuntu 26.04 (prazo externo: 2026-10-19)
Patch: .claude/plans/PLAN-194/wave-w1/w1.patch
Staged: .claude/plans/PLAN-194/wave-w1/staged-w1/.github/workflows/validate.yml
Patch-sha256: TO-FILL-BY-SIGN
Rail-Record-sha256: TO-FILL-BY-SIGN
Anchor-SHA: TO-FILL-BY-SIGN
Data: TO-FILL-BY-SIGN

## Ratificação (Owner)

- Piso do Python, decisão do Owner na S359 (2026-09-30), frase exata: «Manter 3.9 (Recomendado)» —
  a perna 3.9 do CI fica fixada em `ubuntu-24.04`; a alternativa 3.10 saiu do plano.
- Prazo de 2026-10-19, decisão do Owner na S361 (Q6/OQ-2, registrada no PLAN-194, «Decisões do
  Owner — S361»): o Owner fixa a imagem do runner `Ceo` em Ubuntu 24.04 nas configurações da
  organização, fora deste patch, e a W1 segue como planejada.
- PLAN-194, seção W1, itens W1.1 (perna 3.9 num rótulo fixo `ubuntu-24.04`; as outras pernas seguem
  onde estão), W1.2 (os `import yaml` deixam de depender de PyYAML do sistema) e W1.3 (perna 3.14 em
  `ubuntu-26.04` só no `schedule`).

## O que esta cerimônia entrega, e nada além

Um arquivo: `.github/workflows/validate.yml` (77 linhas de diff: 47 entram, 30 saem).

- **W1.1** — o job `hook-tests-python-matrix` escolhe o runner por versão: a perna 3.9 roda no rótulo
  `ubuntu-24.04` em push, pull_request e schedule; 3.10, 3.11 e 3.12 seguem no `Ceo`.
- **W1.3** — no `schedule` (cron `37 7 * * *`), a matriz ganha a perna 3.14, que roda em
  `ubuntu-26.04`. Push segue com 3.9 e 3.12; pull_request, com as quatro (PLAN-184 A0 inalterado).
- **Timeout por perna** — as pernas nos runners padrão (3.9 e 3.14) têm 45 min; as do `Ceo` seguem
  com 25. A letra do plano não fala de timeout: é consequência da W1.1, porque o runner padrão tem
  metade dos núcleos do `Ceo` e a perna 3.9 levou até 646 s na passada paralela e 232 s na serial no
  `Ceo` (runs 36932014761 e 36832647294, 2026-10-01); o comentário do timeout no YAML diz que a
  projeção para o runner padrão é estimativa.
- **W1.2** — o step «Validate settings.json and YAML catalogs» do job `validate` vai, sem mudar uma
  linha do corpo, para depois do `actions/setup-python` e do `pip` que instala o PyYAML. Os comentários
  do bloco do setup-python e do pip passam a dizer que o PyYAML é usado por esse step (antes, o do
  bloco dizia que nenhum uso dele no job estava verificado, e o do pip citava dois testes que já rodam
  na matriz); o do step movido diz que a medição foi em docker, não na imagem do runner.
- **Comentário do custo** — o comentário PLAN-184 A0 da matriz passa a dizer que o custo diário
  citado (~US$ 3,15 de um teto de ~US$ 4,04) foi contado ANTES da W1, com a 3.9 no `Ceo`; não foi
  recalculado.
- **Controle vermelho→verde** — `.claude/plans/PLAN-194/wave-w1/check-w1-shape.py` avalia as
  expressões do runner, do timeout e da matriz para cada evento e versão, e confere a posição do step
  dos catálogos: 9 falhas no `validate.yml` anterior, verde no novo (o SIGN confere as duas pontas).

Não mudam: os outros jobs e steps do `validate.yml`, o template do adopter
(`templates/.github/workflows/validate.yml.template`), os outros workflows em `ubuntu-latest`, o
`.github/actionlint.yaml` e a imagem do runner `Ceo`.

## Evidência (W0.1 e W0.2, medidas entre 2026-10-01 e 2026-10-02, UTC; registro no LEDGER do PLAN-194)

- W0.2: o manifesto do `setup-python` não tem build 3.9 para 26.04; 3.10 e 3.14 têm.
- W0.1, em docker `ubuntu:26.04` (26.04.1 LTS; `python3` 3.14.4, `jq` 1.8.1, `shellcheck` 0.11.0,
  sem PyYAML no sistema), com `ubuntu:24.04` como linha de base:
  (a) o template do adopter ativado e executado: 10/10 steps verdes nas duas imagens (o step dos
  catálogos YAML, pelo fallback do próprio template, que instala o `python3-yaml` pelo apt);
  (b) os 20 steps `run:` do job `validate` antes do setup-python: o mesmo conjunto nas duas imagens —
  só o step dos catálogos YAML reprova (sem PyYAML no sistema) e o `--strict` advisory sai 1 por
  desenho;
  (c) a suíte do job da matriz no `python3` 3.14.4: 13.398 aprovados na passada paralela; na serial,
  1 falha, um teste de orçamento de tempo absoluto que também falha na linha de base 24.04 e no Mac;
  (d) censo dos workflows: 21 workflows com `ubuntu-latest` (28 jobs) e 6 jobs `Ceo`; a única versão
  de Python sem build para 26.04 (3.9) só aparece nesta matriz. Os jobs em `ubuntu-latest` que usam
  o `python3`, o `jq` ou o `shellcheck` da IMAGEM (com ou sem `setup-python`) NÃO foram todos
  executados no 26.04: os que foram, e o resultado de cada um, estão no LEDGER; os que precisam de
  tag ou da API do GitHub não rodaram. Do `ownership-nightly.yml`, os steps 01–08 saíram verdes; no
  09, o conjunto vermelho efetivo é o esperado por desenho (`OWN-0016`, `OWN-0024`, `OWN-0027`)
  depois de rerrodar isoladas as 8 células que estouraram o timeout de 60 s com a VM disputada.
- actionlint 1.7.7 (o binário e o sha256 que o CI usa) e 1.7.12 (local) sobre o `validate.yml` novo:
  verde nas duas formas de invocação do CI. A forma do job `validate` passa as flags do shellcheck no
  `-shellcheck=`, o que DESLIGA a regra shellcheck (medido com `-verbose` no 1.7.12: «Rule "shellcheck"
  was disabled»); a forma do `actionlint.yml` roda o shellcheck (0.9.0 e 0.11.0 medidos).

## Residual declarado (pela forma)

- O actionlint (1.7.7 e 1.7.12) não conhece o rótulo `ubuntu-26.04` e, num `runs-on` com expressão
  composta (`&&`/`||`), não confere os rótulos literais — inclusive o `Ceo`, que antes era conferido
  contra o `.github/actionlint.yaml`. A validade de `ubuntu-24.04` e `ubuntu-26.04` ali vem do anúncio
  do GitHub (actions/runner-images#14748), não do lint; um rótulo escrito errado ali só aparece no run.
- A perna 3.14 roda o setup-python 3.14 do toolcache do runner 26.04, não o `python3` da distro que a
  W0.1 mediu (os dois são 3.14; a W0.1 mediu o 3.14.4 da distro).
- Nenhuma das duas pernas foi medida num runner padrão. A da 3.9 só foi medida no `Ceo` (runs
  36932014761 e 36832647294); a da 3.14, só em docker com 4 CPU (269 s na paralela + 291 s na
  serial). Os 45 min da 3.9 são estimativa a partir do `Ceo`; os da 3.14 seguem os da 3.9 por
  simetria. O primeiro push depois do land mede a 3.9; a primeira noite, a 3.14.
- A perna 3.9 sai do `Ceo` (8 núcleos) para o runner padrão de 4 vCPU e roda em todo push e PR.
  Testes de orçamento de tempo absoluto saíram vermelhos na medição em 4 CPU da W0.1 (o mesmo
  `test_case_a_p99_under_5ms` no 3.14 e no 3.12). Um vermelho dessa classe na perna 3.9 depois do land
  é drift de runner: re-run, nunca cura num corte; a cura estrutural é outra onda.
- A perna 3.14 não tem `continue-on-error`. Se ela sair vermelha, o run noturno do Validate sai
  vermelho, e o plano aceita isso como verde da W1 se o achado for nomeado no LEDGER. As
  consequências: (1) o preflight «CI for HEAD» do `release.sh` reprova quando o run noturno for do
  mesmo commit que se corta e estiver entre os 40 runs mais recentes do repositório, porque julga todo
  run do SHA nessa janela, de qualquer evento; (2) o `scheduled_workflows_red` do `/ceo-boot` acusa o
  run noturno vermelho até que o run completo mais novo do Validate depois dele (de qualquer evento,
  inclusive um cancelado ou de PR) não seja vermelho, e então o dá por curado — um push verde «cura»
  um vermelho da 3.14 que o push não testa; (3) enquanto a 3.14 estiver vermelha, o run noturno vermelho
  esconde, no nível do run, uma regressão nova das pernas 3.10 e 3.11, que o nightly existe para cobrir
  (PLAN-184 A0): é preciso olhar perna por perna.
- Os jobs `Ceo` restantes deste workflow (governança, integração, mutação, dual-rail e as pernas
  3.10–3.12) dependem de o Owner fixar a imagem do `Ceo` em 24.04; os jobs `ubuntu-latest` deste
  workflow (`opus-4-7-profiler-smoke`, `hook-stdout-schema-oracle`) migram para 26.04 com o
  `ubuntu-latest` e usam setup-python 3.11, que tem build para 26.04, mas NÃO foram executados no
  26.04 — nem na W0.1 nem pelo canário, que só roda a suíte da matriz: a primeira evidência deles é a
  própria migração (o gate de latência do profiler é sensível à velocidade do runner).
- O julgamento do actionlint por multiconjunto não vê uma TROCA: o mesmo texto de achado (arquivo,
  mensagem e regra) removido num ponto e acrescentado em outro do mesmo arquivo. Uma ocorrência a
  mais do mesmo texto reprova (a contagem sobe).
- A W1.2 tira a dependência do PyYAML da imagem só neste job; outros workflows que usam o `python3` do
  sistema estão no censo da W0.1 e na W1.5, fora deste patch.

## Bateria e revisão

- O SIGN aplica o patch e confere que o blob do caminho tocado é o `index` pós-imagem do patch — depois
  de aplicar, de novo depois da bateria e, no índice, depois de stagear; confere no P0 que a cópia
  staged tem esse mesmo blob e que o controle da W1 reprova no HEAD; roda o controle sobre os bytes
  aplicados, o actionlint (obrigatório no PATH) nas duas formas do CI, os gates de corpus e as suítes
  do `pytest.ini` com a divisão de marcadores do CI
  (`-n auto -m 'not serial'` e `-m serial`). Uma falha é rerrodada ISOLADA com o patch, até 3 vezes;
  passar em alguma é nota (instável). Se falhar nas 3, é rerrodada uma vez num worktree destacado do
  HEAD (a árvore sem o patch): se lá ela também falha (rc 1 do pytest), é nota (pré-existente) e não
  bloqueia; qualquer outro resultado sem o patch reprova o SIGN. Um gate que reprova com o patch é
  rodado de novo nesse worktree: se também reprova lá, é nota; se passa, reprova o SIGN. O actionlint
  e o validate-governance são julgados também pelo multiconjunto de achados com e sem o patch: no
  actionlint, cada achado com arquivo, mensagem e regra (sem linha e coluna, que o patch desloca); no
  validate-governance, cada linha da saída — cabeçalho, DETALHE de cada violação e contagem `Errors:` —
  menos as linhas de aviso (as que começam, depois dos espaços, com `WARN: `, `WARNING: ` ou
  `WARN (grandfathered): `), a contagem `Warnings: N` e a linha `Repo:`. Uma linha que só existe com o
  patch reprova, mesmo se a base também reprovar;
  uma execução que não chegou a julgar (actionlint com rc fora de 0 e 1, governance sem a linha
  `Errors:`, ou reprovação sem nenhum achado legível) também reprova. O shellcheck é obrigatório no
  PATH, e uma sonda confere que a regra shellcheck do actionlint executa (sem ele, o actionlint sai rc
  0 em silêncio). O controle precisa sair rc 1 com a linha `RESUMO: N falha(s)` no HEAD e rc 0 com
  `RESUMO: verde` com o patch. O HEAD não pode mudar entre as pré-condições e o commit: o Anchor-SHA é
  o pai do commit. O texto assinado é gerado do sentinel do HEAD (o que o rail
  revisou), depois de conferir que o arquivo vivo não mudou durante a bateria; depois do stage, o blob
  do sentinel no índice é o do texto assinado, a assinatura é verificada de novo sobre o índice e tudo
  o que entra no índice tem modo 100644. O patch não pode criar, remover, renomear ou copiar arquivo
  nem mudar modo (recusa nomeada no P0). Um abort desfaz o que o SIGN aplicou e lista, com a receita,
  os arquivos rastreados que a bateria sujou; no `--dry-run`, o «Ensaio OK» só sai com a árvore
  rastreada limpa depois do desfazer.
- A assinatura é feita com `--local-user` pela chave secreta cuja impressão digital está em
  `.claude/sentinel-signers.txt` e precisa verificar contra esse allowlist (GOODSIG e VALIDSIG);
  senão o SIGN desfaz tudo. A escolha da chave e as duas verificações usam o allowlist e a biblioteca
  `_lib/gpg_verify.py` como estão no HEAD, não a árvore viva.
- Rail: regra de parada pré-registrada de no máximo 3 rodadas; registros
  `.claude/plans/PLAN-194/wave-w1/rail-round-N.md`. O SIGN exige que o registro da última rodada nomeie
  os três sujeitos — o sha256 deste patch (`Rail-Subject-sha256`), o deste texto como está no HEAD,
  com os quatro campos ainda por preencher (`Rail-Sentinel-sha256`), e o do `check-w1-shape.py`
  (`Rail-Control-sha256`) —, que `Rail-Reviewer-Verdict` seja o valor da ÚLTIMA linha `VERDICT: ` do
  único bloco verbatim da seção «## Saída do revisor» (a saída do Codex, entre uma linha igual a
  ```` ```text ```` e a próxima linha igual a ```` ``` ````, lida inteira — um título dentro dela não a
  encerra; nenhuma outra linha da seção começa com três crases, nem depois de espaços — quem registra
  cita essas linhas da saída do revisor com o prefixo `> `; seção ausente ou repetida, cerca
  ausente, duplicada, mal formada ou não fechada, ou bloco sem linha `VERDICT: ` recusam o registro) e que o veredito seja `APPROVE` (sem achado; revisor
  em `GO`) ou `DECLARED-P2` (só P2, declarados no próprio registro; revisor em `GO` ou
  `GO-WITH-CONDITIONS`); e vincula esse registro por hash (Rail-Record-sha256) a esta assinatura. O rail
  não revisa o script do SIGN; o ensaio dele é o harness `test-ceremony-w1.sh` (chave GPG descartável,
  clones descartáveis).

## Scope

- `.github/workflows/validate.yml`
