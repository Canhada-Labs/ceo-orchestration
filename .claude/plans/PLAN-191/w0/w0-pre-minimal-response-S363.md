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
| t05 | **sim** | `assert True` com as palavras-chave num comentário | 1,00 | 0,50 | consertado |
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
- **t05** — cobertura por comportamento: os testes do candidato rodam contra a implementação
  de REFERÊNCIA (`_IMPL`), não contra o `solution.py` do diretório, que o candidato podia
  reescrever para uma asserção errada passar; as chamadas a `parse_csv_line` são registradas
  em tempo de execução (0,2 se houve chamada, 0,15 se a linha vazia foi exercitada); 0,15 se
  algum `assert` tem na expressão uma chamada à função (AST — comentário não conta).
- **t07** — o SQL mantém a forma da consulta (`select … from users … where`) e o placeholder
  é o valor comparado a `id` (`%s`, `?`, `:nome`, `%(nome)s`, `$n`). Parâmetros em
  dicionário contam pelos valores: antes, a alternativa válida `:id` + `{'id': user_id}`
  ficava em 0,80 (falso negativo, curado no mesmo patch).
- **t04** — sinal de refatoração = as duas funções públicas definidas E exatamente UM
  `raise` (contado por AST): um helper compartilhado, ou uma função delegando à outra.
  Decisão técnica tomada pelo padrão recomendado na triagem (consertar, não declarar
  aceitável): a instrução pede remover a lógica duplicada, e a solução de referência já tem
  um único teste de negativo. Se o Owner preferir «aceitável», basta reverter o sinal do t04.

## Controles

- **Vermelho:** os onze payloads de `MINIMAL_RESPONSES`
  (`.claude/scripts/tests/test_eval_c3.py`, classe `TestMinimalResponse`) davam 1,00 nos
  verificadores de `38d56f35`; com o patch, nenhum passa de 0,80. O teste
  `test_minimal_response_does_not_score_full` falhava na árvore anterior
  (`1.0 not less than 0.99`).
- **Mutante:** reverter UM dos quatro verificadores de cada vez deixa o teste vermelho (4 de 4).
- **Verde:** GOLDEN 10 de 10 = 1,00; árvore inicial sem mudança (t04 0,80, demais 0,00);
  `VALID_ALTERNATIVES` 3 de 3 = 1,00 (`test_valid_alternative_keeps_full_reward`); o arquivo
  de teste inteiro passa (30 testes).

## Residuais declarados

- Os seis verificadores restantes medem comportamento (casos de entrada e saída) e não aceitam
  resposta mínima; aceitam qualquer implementação correta (o t10 aceita uma busca linear).
  Isso é aderência à instrução, outra classe, fora do W0-pre.
- Um verificador determinístico não julga semântica: um README com título, uma frase de três
  palavras quaisquer, um bloco que chama `add(` e as três funções nomeadas ainda chega a 1,0.
  Por isso o W1 já pré-registra o juiz cego ao braço para medir escapes.
- `.claude/eval/README.md` cita `.github/workflows/eval-nightly.yml` como proposta do
  PLAN-133; o arquivo não existe em `.github/workflows/`. Consertar os verificadores só muda,
  no CI, o resultado de `test_eval_c3.py`.

## Gate do W0

Com esta nota, o W0-pre está fechado: o critério do W0 («`t09` consertado ou excluído ANTES
da primeira tentativa») está satisfeito, e os outros três verificadores fracos também.
