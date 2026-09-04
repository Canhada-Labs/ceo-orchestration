# PLAN-186 W4a — RESULTADO da deleção dos dois steps duplicados

> Gerado por `.claude/plans/PLAN-186/OWNER-S343-W4A-MEASURE.sh` na cerimônia `wave-s343-w4a`.
> **Este documento é subtração bruta de medições. Não há previsão, alvo
> nem claim de velocidade** (`AGENTS.md:9-11`): os números abaixo dizem o
> que as seis execuções custaram, e o AC-6/AC-11 são julgados pelo Owner
> sobre eles.


## 1. O que foi comparado

- **Baseline (pré-deleção):** os TRÊS runs REGISTRADOS por id no §6 de
  `validate-deletion-measure-S340.md` — nunca «os últimos runs do main».

> **RESSALVA CARIMBADA — leia antes de subtrair.** Os baselines NÃO
> rodaram no mesmo commit: `b6dce787651aaa9c06e842ce9d665cfb9d201ecd 400638eb62bae42e0a3a3e9b10a0a058012a6e73 8efe09b7484ffb9d25fa393df47a5c8002597bb1`.
> Entre o baseline mais antigo e o `HEAD` medido há **16 commit(s)** e
> **125 arquivo(s)** de diferença, e um deles alterou arquivos que o CI
> executa (§6 do relatório da S340 declara, literalmente, que esta tabela
> «é o registro do que existia, não o baseline definitivo»). O Owner
> reconheceu o drift com `CEO_W4A_BASELINE_DRIFT_ACK=I-ACCEPT`.
> **Consequência:** a subtração abaixo é entre commits DIFERENTES. Parte
> da diferença é carga que mudou entre eles, não a deleção. Fechar o
> AC-6/AC-11 sobre ela sem descontar isso atribuiria à deleção um efeito
> que ela não teve.

- **Deleção (pós):** a corrida 1/3 é o push do LAND (`8003b65`); as corridas
  2 e 3 são commits VAZIOS, empurrados SERIALIZADOS (o
  `concurrency.cancel-in-progress` do `validate.yml` cancela runs
  consecutivos, e um leg cancelado reporta `cancelled`).
- **Wall do RUN** = `startedAt`→`updatedAt` do run (`completedAt` não é
  campo de run no `gh`; é campo de JOB). **Minutos por classe de runner**
  = soma de `startedAt`→`completedAt` de cada JOB, com a classe DERIVADA
  do `runs-on` do próprio `validate.yml` (o `gh` não expõe o label).

## 2. Baseline (pré-deleção, 3 runs registrados)

| run | sha | conclusion | RUN wall | job `validate` | min `Ceo` | min `ubuntu-latest` | maior job restante |
|---|---|---|---|---|---|---|---|
| `33709753629` | b6dce78 | success | 20m00s | 19m57s | 53.85 | 2.12 | 19m57s — Governance, health, contamination, shellcheck |
| `33656365016` | 400638e | success | 21m45s | 20m39s | 54.80 | 2.27 | 20m39s — Governance, health, contamination, shellcheck |
| `33630753334` | 8efe09b | success | 21m02s | 20m58s | 54.23 | 2.12 | 20m58s — Governance, health, contamination, shellcheck |
| **média** | — | — | 20m56s | 20m31s | 54.29 | 2.17 | — |

## 3. Deleção (pós, 3 runs serializados)

| run | sha | conclusion | RUN wall | job `validate` | min `Ceo` | min `ubuntu-latest` | maior job restante |
|---|---|---|---|---|---|---|---|
| `33874751641` | 8003b65 | success | 11m29s | 8m15s | 42.88 | 2.07 | 11m08s — hook-tests-python-matrix (3.9) |
| `33875799896` | 0bd0620 | success | 10m45s | 8m06s | 36.67 | 2.15 | 9m12s — hook-tests-python-matrix (3.9) |
| `33876800710` | 532ad22 | success | 12m27s | 8m00s | 45.33 | 2.08 | 12m23s — hook-tests-python-matrix (3.12) |
| **média** | — | — | 11m34s | 8m07s | 41.63 | 2.10 | — |

## 4. Subtração (média pós − média baseline)

| grandeza | baseline | deleção | delta |
|---|---|---|---|
| RUN wall | 20m56s | 11m34s | −9m22s |
| job `validate` | 20m31s | 8m07s | −12m24s |
| minutos `Ceo` | 54.29 | 41.63 | -12.67 |
| minutos `ubuntu-latest` | 2.17 | 2.10 | -0.07 |

**Como ler — e o que estes números NÃO dizem.** As colunas acima são a
SUBTRAÇÃO BRUTA entre dois conjuntos de runs. Elas **não** isolam o custo
dos dois steps deletados: os baselines rodaram em commits diferentes
(ressalva carimbada na §1), e parte do delta é carga que mudou entre
eles. Atribuir o delta inteiro à deleção seria um claim de velocidade
sem baseline controlado — proibido por `AGENTS.md:9-11`.

O que se pode dizer com o que está medido: o delta do RUN wall tende a
ser MENOR que o delta do job `validate`, porque o run termina quando o
ÚLTIMO job termina e o piso passa a ser outro job — a coluna «maior job
restante» diz qual. Um número causal exige o que o §6 do relatório da
S340 já pedia: três baselines RE-RODADOS num único sha pré-deleção.

## 5. Cobertura — o que NÃO mudou

A união exata dos node-ids dos dois steps deletados é o que
`hook-tests-python-matrix` já roda, em 3.9 e 3.12. A igualdade foi
RE-DERIVADA por conjunto (sha256 da lista ordenada) no V5 do LAND, sobre
a árvore que foi landada — não citada de um relatório anterior.

## 6. Perdas de ambiente ACEITAS e declaradas

| variável | antes | depois | por quê |
|---|---|---|---|
| `PYTHONPATH: "."` | ausente nos 2 steps, presente na matriz | SEMPRE presente | recuperar exigiria dimensão de matriz que dobra o custo do job pago |
| `CEO_HOOK_ADAPTER: claude` | só no step A (que rodava só hooks) | SEMPRE ausente | a matriz roda hooks+scripts+optimizer num único pytest; setá-la ALTERARIA o ambiente de scripts/optimizer. É o default documentado do adapter |

