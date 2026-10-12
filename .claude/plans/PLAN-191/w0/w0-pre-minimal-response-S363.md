# PLAN-191 W0-pre — «resposta mínima» nos dez verificadores (S363, 2026-10-12)

Item W0-pre do PLAN-191 (pré-condição do W0, livre, sem quota). «Resposta mínima» é a
saída mais vazia que ainda tem a forma esperada. Base medida: `38d56f35`. Oráculo
`check_canonical_edit.py --is-canonical` = 0 nos oito paths do pacote (rodado na
sombra antes de editar).

## Resultado por tarefa

| tarefa | aceitava resposta mínima? | resposta mínima medida | antes | depois | ação |
|---|---|---|---|---|---|
| t01 | não | `return 0` | 0,00 | 0,00 | nenhuma |
| t02 | não | `return []` | 0,00 | 0,00 | nenhuma |
| t03 | não | `return dict(DEFAULTS)` | 0,67 | 0,67 | nenhuma |
| t04 | **sim** | apagar só os 9 caracteres ` or s < 0` | 1,00 | 0,80 | consertado |
| t04 | **sim** | apagar o teste de negativo de `area_rectangle` (rodada de refutação) | 1,00 | 0,73 | consertado |
| t05 | **sim** | `assert True` com as palavras-chave num comentário | 1,00 | 0,50 | consertado |
| t05 | **sim** | religar o nome do resultado (`for`, `with`, walrus, `def` aninhado, ramo morto, mesma linha) ou tautologia (pacote 191-A2) | 1,00 | 0,50 | consertado por mutação |
| t06 | não | `return True` | 0,75 | 0,75 | nenhuma |
| t07 | **sim** | `return ('?', (user_id,))` (nem é SQL) | 1,00 | 0,20 | consertado |
| t08 | não | `return {}` | 0,25 | 0,25 | nenhuma |
| t09 | **sim** | README só com `# add subtract multiply usage` | 1,00 | 0,15 | consertado |
| t10 | não | `return -1` | 0,43 | 0,43 | nenhuma |

Nenhuma tarefa foi excluída: as dez seguem disponíveis para a seleção do W0/W1.

## A classe e as curas

Os quatro verificadores fracos pontuavam a PRESENÇA de uma palavra ou de uma forma, não o
conteúdo. As curas medem cada parte pela própria forma ou pelo comportamento:

- **t09** — tudo é medido ABAIXO da linha de título: descrição = uma linha de prosa com
  ≥ 3 palavras além dos nomes da API; exemplo de uso = bloco cercado que importa `calc` ou
  chama uma das funções; cada função = palavra inteira. Pesos 0,15 (título) + 0,15 + 0,25 +
  3 × 0,15.
- **t05** — cobertura por MUTAÇÃO (pacote 191-A2; substitui a regra de AST e fluxo de dados,
  que em três rodadas não convergiu: cada cura deixava uma fuga). Os testes do candidato rodam
  contra a implementação de REFERÊNCIA (`_IMPL`), nunca contra o `solution.py` do diretório,
  que o candidato podia reescrever para uma asserção errada passar, antes e depois dos
  mutantes; falhar ali dá 0,00. Quatro mutantes fixos no próprio verificador quebram, cada um,
  um comportamento documentado (linha vazia devolve `['']`; campos sem `strip`; separador
  `;`; último campo descartado); um mutante está MORTO quando o arquivo do candidato não passa
  contra ele. Nota = 0,5 + 0,5 × mortos ÷ 4. A forma sintática da asserção deixa de importar.
  A implementação sob teste entra no namespace DEPOIS que o módulo de teste roda (definição
  sombra perde) e como módulo `solution` durante a carga: `from solution import
  parse_csv_line` passa a valer 1,00 (dava 0,00 desde `38d56f35`).
- **t07** — o SQL mantém a forma da consulta (`select … from users … where`) e o placeholder
  é o valor comparado a `id` (`%s`, `?`, `:nome`, `%(nome)s`, `$n`). Parâmetros em
  dicionário contam pelos valores: antes, a alternativa válida `:id` + `{'id': user_id}`
  ficava em 0,80 (falso negativo, curado no mesmo patch).
- **t04** — sinal de refatoração = as duas funções públicas definidas E exatamente UM
  `raise` (contado por AST): um helper compartilhado, ou uma função delegando à outra. Os
  negativos são exercitados nas DUAS funções (`area_square(-2)`, `area_rectangle(-1, 2)` e
  `(2, -1)`): apagar o teste de `area_rectangle` também deixa um único `raise`.
  Decisão técnica tomada pelo padrão recomendado na triagem (consertar, não declarar
  aceitável): a instrução pede remover a lógica duplicada, e a solução de referência já tem
  um único teste de negativo. Se o Owner preferir «aceitável», basta reverter o sinal do t04.

## Controles

- **Vermelho:** os onze payloads da primeira versão de `MINIMAL_RESPONSES`
  (`.claude/scripts/tests/test_eval_c3.py`, classe `TestMinimalResponse`) davam 1,00 nos
  verificadores de `38d56f35`; com o patch, nenhum passa de 0,80. A lista cresceu nas rodadas de
  refutação e hoje tem 23 payloads; o teste exige de TODOS menos que o limiar de PASS do runner
  (0,99). O payload-guarda do t05 (chama a função, mas o `assert` não lê o resultado) ficava em
  0,85 e, com a mutação, fica em 0,50. Na rechecagem (S363) entraram mais dois do t05, a ligação
  ao resultado só DEPOIS do `assert` e a religação a outro valor antes dele: davam 1,00 em
  `38d56f35`, 0,85 em `2e1d8135` e 0,50 com a mutação. O teste
  `test_minimal_response_does_not_score_full` falhava na árvore anterior
  (`1.0 not less than 0.99`).
- **Troca de arquitetura do t05 (pacote 191-A2, S363):** a rechecagem de `2e1d8135` achou seis
  fugas da regra de texto. Medido, verificador de `2e1d8135` → verificador por mutação: as seis
  fugas e a tautologia `assert r == r`, 1,00 → 0,50; teste sem o caso da linha vazia, 0,85 →
  0,875 (controle do mutante da linha vazia); formas legítimas completas (caso básico e linha
  vazia) em uma linha, com `try/except`, com walrus em `if`, 0,85 → 1,00; com anotação
  (`result: list = ...`), 1,00 → 1,00; com `from solution import parse_csv_line`, 0,00 → 1,00.
  Vermelho: o verificador de `2e1d8135` com o arquivo de teste novo dá `2 failed`
  (`minimal t05-add-unit-test#6 scored 1.0` e `valid alternative t05-add-unit-test#1 scored
  0.85`). Mutantes do verificador, 4 de 4 vermelhos: sem a segunda rodada da referência (um
  teste que conta as próprias cargas passa só na primeira rodada e chega a 1,00); sem o módulo
  `solution` (a forma com `import` cai a 0,00); sem o mutante da linha vazia (o teste sem caso
  vazio chega a 1,00); referência lida do `solution.py` do diretório (a reescrita chega a 1,00).
  Desvio DECLARADO da cláusula de prova do pacote 191-A2, que pedia 1,00 para a forma de uma
  linha `r = parse_csv_line(''); assert r == []`: essa forma só verifica a linha vazia, mata 1
  de 4 mutantes e fica em 0,625 (abaixo do PASS de 0,99). A própria cláusula se contradiz
  (os mutantes de `strip`, separador e último campo que ela pede não morrem com um teste só do
  caso vazio). Padrão técnico adotado: a instrução pede o comportamento «incluindo» o caso
  vazio, então as formas legítimas entram nos controles como testes completos. Aceitar ou não
  o teste só do caso vazio é decisão de produto, reservada ao Owner, não ao construtor; se ele
  preferir aceitá-lo, basta tirar os outros três mutantes. A escolha vigente fica fixada por
  teste (`test_t05_partial_tests_score_exactly_as_declared`, valor exato 0,625).
- **Mutante:** reverter UM dos quatro verificadores de cada vez deixa o teste vermelho (4 de 4).
- **Rodada de refutação (sobre `0bf1e824`):** dois achados P2 confirmados por sonda e curados.
  t04: o payload que apaga o teste de negativo de `area_rectangle` dava 1,00 e fica em 0,73
  (vermelho antes, verde depois). t05: o estilo `result = parse_csv_line(...)` + `assert result
  == ...` ficava em 0,85, abaixo do limiar de PASS do runner (0,99) — falso negativo; agora
  1,00, controle em `VALID_ALTERNATIVES`. Payload-guarda (chama a função, mas o `assert` não lê
  o resultado): 0,85 antes e depois. Mutantes vermelhos: só `area_square` testado no negativo;
  sem o passo de dataflow; crédito para qualquer `assert` de função que chama a função. (A regra
  de fluxo de dados do t05 saiu no pacote 191-A2; ver o item seguinte.)
- **Verde:** GOLDEN 10 de 10 = 1,00; árvore inicial sem mudança (t04 0,80, demais 0,00);
  `VALID_ALTERNATIVES` 9 de 9 = 1,00 (6 do t05, aceitos como lista;
  `test_valid_alternative_keeps_full_reward`); o arquivo de teste inteiro passa (32 testes).

## Residuais declarados

- Os seis verificadores restantes medem comportamento (casos de entrada e saída) e não aceitam
  resposta mínima; aceitam qualquer implementação correta (o t10 aceita uma busca linear).
  Isso é aderência à instrução, outra classe, fora do W0-pre.
- Um verificador determinístico não julga semântica: um README com título, uma frase de três
  palavras quaisquer, um bloco que chama `add(` e as três funções nomeadas ainda chega a 1,0.
  No t05, o `assert` tautológico (`r == r` com `r = parse_csv_line('')`), que chegava a 1,0,
  fica em 0,50 com a mutação. Residuais do t05 por mutação: um teste que inspeciona a
  implementação (bytecode, closure) em vez de chamá-la pode distinguir os mutantes sem testar
  comportamento; estado guardado fora do namespace (builtins, arquivo) por quem conhece a ordem
  das rodadas escapa da segunda rodada da referência, que fecha só o contador ingênuo; o
  verificador não tem limite de tempo, e um laço que dependa do resultado pode não terminar
  contra um mutante; quatro mutantes cobrem só os três comportamentos documentados.
  Por isso o W1 já pré-registra o juiz cego ao braço para medir escapes.
- Falso negativo do t05 por mutação (classe nova do pacote 191-A2): com quatro mutantes e PASS
  em 0,99, a nota exige que o teste afirme os quatro comportamentos (`strip` dos campos,
  vírgula como separador, todos os campos, linha vazia). Agora são as ENTRADAS do teste, e não
  a forma da asserção, que decidem a nota: um teste correto que deixa um comportamento de fora
  fica entre 0,75 e 0,875 e reprova. Medido (verificador de `2e1d8135` → mutação): `'a,b,c'`
  mais a linha vazia, 1,00 → 0,875 (sem espaço dentro dos campos, o mutante sem `strip`
  devolve o mesmo resultado e sobrevive); `' a '` mais a linha vazia, 1,00 → 0,75 (o espaço
  das pontas sai no `strip` da linha inteira, antes do `split`: sobrevivem o mutante sem
  `strip` e o do separador); `'a'` mais a linha vazia, 1,00 → 0,75. O `strip` dos campos está na docstring de `parse_csv_line`, não
  na instrução. Esses valores ficam fixados em `test_t05_partial_tests_score_exactly_as_declared`.
  Alinhar a instrução ao conjunto de mutantes, ou mudar o limiar ou os mutantes, fica para o
  Owner, depois que o juiz cego do W1 medir com que frequência candidatos reais caem nessa
  faixa.
- `.claude/eval/README.md` cita `.github/workflows/eval-nightly.yml` como proposta do
  PLAN-133; o arquivo não existe em `.github/workflows/`. Consertar os verificadores só muda,
  no CI, o resultado de `test_eval_c3.py`.

## Gate do W0

Com esta nota, o W0-pre está fechado: o critério do W0 («`t09` consertado ou excluído ANTES
da primeira tentativa») está satisfeito, e os outros três verificadores fracos também.
