# PLAN-186 W4a (AC-16) — Medição da deleção dos dois steps de pytest duplicados do job `validate`

> **Estado: PRÉ-REGISTRO.** As três execuções **ainda não aconteceram** quando este
> documento foi escrito. O que está abaixo dos números de baseline é o que SERÁ
> comparado, COMO, e com quais comandos exatos. A tabela de resultados está
> deliberadamente VAZIA — o CEO a preenche depois que o Owner rodar a cerimônia da W4 (§9).
>
> Sessão S340 (2026-09-03), assento Opus 5. Confinamento: este agente **não editou
> nenhum arquivo sob `.github/`** em árvore, branch ou worktree nenhuma. O
> entregável é uma CÓPIA no scratchpad mais um cerimônia da W4 (§9) que o Owner executa à mão.

---

## 1. A claim, verificada no disco (não de memória)

Tudo abaixo foi lido de `.github/workflows/validate.yml` em `main @ ba15c71`.

| Sítio | Linha | Fato verificado |
|---|---|---|
| job `validate` | `:30` | `name: Governance, health, contamination, shellcheck` |
| job `validate` | `:36` | `runs-on: Ceo` (runner maior, **PAGO** por budget de org) |
| step A | `:454` | `- name: Run Python hook unit tests (CEO_HOOK_ADAPTER=claude default)` |
| step A env | `:455-456` | `env:` / `CEO_HOOK_ADAPTER: claude` |
| step B | `:539` | `- name: Run Python script unit tests` |
| job matriz | `:1606` | `hook-tests-python-matrix`, `runs-on: Ceo`, `fail-fast: false` |
| matriz env | `:1637-1638` | `env:` / `PYTHONPATH: "."` |
| matriz legs | `:1626-1630` | em `push`: `["3.9","3.12"]`; nos demais eventos: as quatro |

### Listas de argumentos EXATAS (o input da comparação de node-ids)

Step A (`:461-462`) — sem `PYTHONPATH`, com `CEO_HOOK_ADAPTER=claude`:

    python3 -m pytest .claude/hooks/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q
    python3 -m pytest .claude/hooks/tests/ -m 'serial' --strict-markers --tb=no -q

Step B (`:544-545`) — sem `PYTHONPATH`, sem `CEO_HOOK_ADAPTER`:

    python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q
    python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -m 'serial' --strict-markers --tb=no -q

Matriz (`:1642-1645`) — com `PYTHONPATH="."`, sem `CEO_HOOK_ADAPTER`:

    python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/ \
      -n auto -m 'not serial' --strict-markers --tb=no -q
    python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/ \
      -m 'serial' --strict-markers --tb=no -q

**Correção a um número do plano.** A W4a cita «5m57s + 8m05s = 14m02s dos 22m22s».
Medido agora nos 3 últimos runs verdes de `push` em `main`, os números envelheceram:
os dois steps custam **12m01s / 12m18s / 13m00s** (média **12m26s**) dentro de um job
`validate` de **19m57s / 20m39s / 20m58s** (média **20m31s**). A ordem de grandeza da
decisão não muda; o número citado, sim.

---

## 2. Comparação de node-ids — o gate de cobertura

Instrumento: `pytest --collect-only -q -p no:cacheprovider` com `PYTHONDONTWRITEBYTECODE=1`,
o MESMO interpretador (`Python 3.9.6`) para os três conjuntos, cada um nos DOIS passes
(`-m 'not serial'` e `-m 'serial'`), unidos e `sort -u`.

| Conjunto | node-ids |
|---|---|
| A = step A (hooks) | **7 474** |
| B = step B (scripts + optimizer) | **6 063** |
| A ∩ B | **0** (raízes disjuntas, como esperado) |
| **A ∪ B** | **13 537** |
| **Matriz** | **13 537** |
| (A ∪ B) − matriz | **0** |
| matriz − (A ∪ B) | **0** |

`sha256` das duas listas ordenadas: **idêntico** (`361d8cddbe676a98…`) — igualdade de
CONJUNTO, não contagem coincidente.

**Perna extra, não pedida pelo AC mas load-bearing:** a partição serial/não-serial
também bate. `serial`: A=492, B=432, A∪B=**924**, matriz=**924**, diferença **0** nos
dois sentidos. Sem essa perna, um teste que trocasse de passe passaria despercebido —
é exatamente a «edição de uma linha que não produz vermelho nenhum» do C-K14.

**Veredito de cobertura: a deleção NÃO é recusada.** A matriz já executa, em 3.9 e 3.12,
a união exata dos dois steps.

### Ressalvas declaradas da medição

1. `pytest 7.3.0` local vs `pytest==8.*` na CI. A coleta é estável entre as duas para
   esta suíte, mas a igualdade foi provada com 7.3.0 — a execução real na branch é o
   controle que fecha isso.
2. Coleta local em 3.9.6; a matriz cobre 3.9 **e** 3.12. A perna 3.12 não foi coletada
   localmente.
3. `-n auto` foi retirado das invocações de coleta: sob xdist o `--collect-only -q`
   imprime contagem por arquivo, não node-ids. `-n` é flag de paralelização e não altera
   o conjunto coletado. **Armadilha paga nesta medição:** o `-q` do step somado ao `-q`
   do invocador vira `-qq` e degrada a saída para `arquivo: N` — a primeira rodada saiu
   assim e foi descartada.

---

## 3. O delta de ambiente DUPLO, DECLARADO

> **Errata do rail r17 (P2):** a primeira redação ADICIONAVA `CEO_HOOK_ADAPTER: claude` ao step da
> matriz para «preservar a união». Isso é FALSO como identidade: o step A deletado setava a variável
> só para `.claude/hooks/tests`, e o step da matriz roda hooks + scripts + optimizer num único
> `pytest` — setá-la ali ALTERARIA o ambiente de scripts/optimizer (que rodavam com ela AUSENTE no
> step B e na matriz). Como `claude` é o default documentado do adapter, a ausência exercita o
> mesmo caminho que o step A exercitava explicitamente. As DUAS cópias não a setam mais; o delta
> (1) abaixo passa de «adicionado» para «perda ACEITA, mesmo caminho pelo default».

| Variável | Steps deletados | Matriz (hoje) | Tratamento |
|---|---|---|---|
| `CEO_HOOK_ADAPTER: claude` | presente **só no step A** | **ausente** | **NÃO adicionado (perda ACEITA — errata r17)** à matriz na cópia — a união de ambientes é preservada |
| `PYTHONPATH: "."` | **ausente nos dois** | presente | **NÃO recuperável sem custo** — ver abaixo |

`CEO_HOOK_ADAPTER: claude` é o default explícito do adapter (o próprio nome do step diz
«default»); por isso a AUSÊNCIA na matriz exercita o mesmo caminho — e setá-lo lá alteraria
scripts/optimizer (errata r17). Decisão: não levar.

`PYTHONPATH` é o caso assimétrico e a **perda de cobertura real desta deleção**: hoje a
suíte roda em DUAS configurações — com e sem `PYTHONPATH="."` — e depois da deleção só
resta a COM. Evidência de que o risco é baixo, não nulo: existe `conftest.py` na raiz do
repo, então o pytest já insere o rootdir em `sys.path` (import mode `prepend`), o que
torna `PYTHONPATH="."` majoritariamente redundante; e a coleta local foi **idêntica**
com e sem a variável. Isso é evidência sobre COLETA, não sobre IMPORTS em tempo de
execução. **Declarado como perda aceita**; recuperá-la exigiria uma dimensão de matriz
que dobraria o custo — exatamente o que a wave quer evitar. Se a W4b quiser fechá-la, o
lugar é uma dimensão da matriz nova, não um step ressuscitado no `validate`.

---

## 4. A rota usada, e por que ela NÃO é «push na branch»

> **Errata do rail r15 (P1 — decisão de arquitetura, S341):** o «kit do Owner» que a primeira
> redação entregava (`OWNER-W4A-BRANCH-KIT.sh` / `OWNER-W4A-COLLECT.sh`) foi RETIRADO do repo.
> Ele editava e commitava `.github/workflows/validate.yml` numa branch sem sentinel assinado —
> `AGENTS.md:86-91,110` guarda essa árvore, e um script que contorna o guard por ser «rodado
> pelo Owner à mão» é a forma exata de permission laundering que o classificador do harness
> recusou no E original. A execução das 3 corridas é, por construção, parte da CERIMÔNIA da W4
> (sentinel + assinatura), e o que este relatório entrega é o INSUMO dela: a prova de cobertura
> (§2), o delta de ambiente (§3), as duas cópias do YAML (`.txt`) e os baselines (§6). O
> segundo defeito do a cerimônia da W4 (§9) (pinar a branch em `ba15c71` apagava o próprio `.txt` que ele lia) não
> precisa de cura: o a cerimônia da W4 (§9) não existe mais.

**Rota: worktree/branch descartável operada pelo OWNER**, não por agente. Nenhum arquivo
sob `.github/` foi tocado em árvore viva — o hook de edição canônica
(`check_canonical_edit.py:183-185`) guarda `.github/workflows/*.yml` e essa guarda é a
fronteira desta tarefa. O agente produziu uma CÓPIA no scratchpad.

**Achado que muda o desenho da medição:** `validate.yml:4-5` declara

    push:
      branches: [main]

Um push para a branch descartável **não dispara nada**. E medir via `pull_request`
inviabiliza a comparação: o `fromJSON` em `:1626-1630` expande a matriz para **quatro**
legs de Python fora do `push`, contra duas — outra conta de minutos, outro wall.

Por isso há **duas** cópias:

| Arquivo | O quê | `sha256` |
|---|---|---|
| `validate.deletion.yml` | a deleção LIMPA (o que a W4b landaria) | `669206568d9ef523…669206568d9ef523` |
| `validate.deletion.measure.yml` | a mesma, **mais** a branch em `on.push.branches` | `fb71fd8bfac4e9f3…fb71fd8bfac4e9f3` |

A linha extra é **MEASURE-ONLY** e está comentada como tal na própria cópia; ela existe
só para que os 3 runs disparem no MESMO evento (`push`, 2 legs) dos baselines. **Reverter
antes da W4b.** O a cerimônia da W4 (§9) recusa rodar se receber a variante limpa.

Segundo risco desenhado para fora: `concurrency.cancel-in-progress: true` agrupado por
`github.ref` (`:20-22`). Três pushes seguidos na mesma branch **cancelariam** os runs
anteriores — a assinatura `cancelled` que este repo já confundiu com estouro de timeout.
O a cerimônia da W4 (§9) portanto **espera** cada run terminar (`gh run watch`) antes do push seguinte.

### `actionlint`

Disponível localmente. Rodado sobre as DUAS cópias **com** `.github/actionlint.yaml`
(que declara o label `Ceo`): **rc=0, zero achados**, igual ao controle sobre o arquivo
vivo. Sem esse config, os 5 `runs-on: Ceo` viram falso-positivo `runner-label` — a
primeira execução saiu assim e foi descartada.

---

## 5. O diff

> Errata r17/r21: o diff documentado na primeira redação mostrava `+ CEO_HOOK_ADAPTER: claude`
> no step da matriz. As cópias `.txt` commitadas NÃO adicionam a chave (ver §3). O diff
> autoritativo é o das próprias cópias contra `.github/workflows/validate.yml` em `ba15c71`:
>
> ```
> git diff --no-index .github/workflows/validate.yml .claude/plans/PLAN-186/w4/validate.deletion.yml.txt
> ```
>
> Resumo do que ele contém: (1) os dois steps `Run Python hook unit tests (CEO_HOOK_ADAPTER=claude default)`
> e `Run Python script unit tests` REMOVIDOS do job «Governance, health, contamination, shellcheck»;
> (2) no step da matriz, um COMENTÁRIO explicando por que `CEO_HOOK_ADAPTER` não é setado;
> (3) o comentário em `:330-331` atualizado para apontar a matriz em vez do step deletado;
> (4) na variante MEASURE, a branch `plan186/w4a-validate-deletion-s341` em `on.push.branches`.

## 6. Baselines JÁ medidos (3 runs verdes de `push` em `main`)

> **Ressalva do rail r25 (P2): os 3 baselines abrangem TRÊS commits** — `33630753334` rodou em
> `8efe09b`, `33656365016` em `400638e`, `33709753629` em `b6dce78` — e `b6dce78` alterou arquivos
> que o CI executa. O branch de medição está ancorado em `ba15c71`. A cerimônia da W4 deve ou
> (a) re-rodar 3 baselines em `ba15c71` ANTES da deleção (mesma branch, sem a cópia), ou (b)
> declarar o drift entre `8efe09b..ba15c71` como aceito, com o diff dos arquivos executados pelo CI.
> A tabela abaixo é o registro do que existia, não o baseline definitivo.

> **Nomenclatura (conferência independente da sessão irmã `c0`, S341 — os 12 números abaixo batem
> EXATAMENTE com `gh api runs/<id>` + `runs/<id>/jobs`, zero divergência):** não existe job com
> `name: validate`. O que este relatório chama de «job `validate`» é o job cujo **display name** é
> **«Governance, health, contamination, shellcheck»** (19m57s / 20m39s / 20m58s). Quem reproduzir pelo
> nome deve procurar por esse display name — ou pelo id do job — nunca por «validate».

| Run | RUN wall | job `validate` | min `Ceo` (PAGO) | min `ubuntu-latest` (GRÁTIS) |
|---|---|---|---|---|
| `33709753629` | 20m00s | 19m57s | 53,85 | 2,12 |
| `33656365016` | 21m45s | 20m39s | 54,80 | 2,27 |
| `33630753334` | 21m02s | 20m58s | 54,23 | 2,12 |
| **média** | **20m56s** | **20m31s** | **54,29** | **2,17** |

### Aritmética de subtração (NÃO é previsão — `AGENTS.md:9-11` proíbe claims de speedup)

Este repositório não faz claim de throughput. O que fica aqui é a SUBTRAÇÃO do custo medido dos
dois steps de cada run, como dado bruto para a comparação de AC-6/AC-11 DEPOIS das corridas:

| Run | `validate` − (A+B) | maior job restante |
|---|---|---|
| `33709753629` | 7m56s | 11m18s — `hook-tests-python-matrix (3.9)` |
| `33656365016` | 8m21s | 11m09s — `hook-tests-python-matrix (3.9)` |
| `33630753334` | 7m58s | 10m36s — `hook-tests-python-matrix (3.9)` |

Nenhuma dessas linhas é o resultado da medição: o resultado é a tabela de corridas do §7, vazia até
o Owner rodar a cerimônia da W4 (§9). AC-6 e AC-11 são julgados SÓ sobre corridas reais (`startedAt`→`completedAt`
do RUN, minutos por classe de runner), nunca sobre esta subtração.

## 7. RESULTADOS — **A PREENCHER PELO CEO** depois que o Owner rodar a cerimônia da W4 (§9)

> Preencher DENTRO da cerimônia da W4, com `gh run view <id> --json jobs` sobre os 3 runs da branch e os 3 baselines REGISTRADOS por id (§6) — nunca «os últimos de main».

| Run (deleção) | id | conclusion | RUN wall | job `validate` | min `Ceo` | min `ubuntu` |
|---|---|---|---|---|---|---|
| 1 | _(vazio)_ | | | | | |
| 2 | _(vazio)_ | | | | | |
| 3 | _(vazio)_ | | | | | |
| **média** | — | | | | | |

| Comparação | baseline | deleção | delta | % |
|---|---|---|---|---|
| RUN wall | 20m56s | _(vazio)_ | | |
| job `validate` | 20m31s | _(vazio)_ | | |
| min `Ceo` (PAGO) | 54,29 | _(vazio)_ | | |
| min `ubuntu-latest` (GRÁTIS) | 2,17 | _(vazio)_ | | |

- [ ] Os 3 runs terminaram **verdes**.
- [ ] Nenhum step perdido além dos dois deletados (conferir a lista de steps em
      `gh run view <id> --json jobs`).
- [ ] Piso de jobs observado == `hook-tests-python-matrix (3.9)`.
- [ ] AC-6: RUN wall ≤ 14 min nos 3.
- [ ] AC-11: `Ceo` ≤ 1,3 × 54,29 = 70,6 min.

**Veredito AC-16 — a preencher:** `deleção viável` / `recusada por cobertura` /
`recusada por falha`.
Pela cobertura (§2) a recusa já está **descartada**; resta o braço de execução.

---

## 8. O que a W4b leva daqui

1. **Deleção e split são complementares** (K21) e a deleção **vem primeiro**. O que está
   MEDIDO: cobertura (§2) e delta de ambiente (§3). O que NÃO está medido: qualquer efeito em
   wall-clock ou minutos — o §7 está vazio até as 3 corridas da cerimônia. A justificativa do
   split é de ESTRUTURA (atribuição independente de falha, `if: always()` por job), e ela não
   depende do §7.
2. **O piso a citar é a perna 3.9**, não a 3.12 — nos 3 baselines (§6).
3. **`PYTHONPATH: .` e `CEO_HOOK_ADAPTER`** são as duas perdas de ambiente ACEITAS (§3);
   a W4b as herda como decisão, não as re-discute.

## 9. Artefatos e a branch

Todos os artefatos vivem no diretório de scratchpad desta sessão, `<scratchpad>/deliverables/w4/`:

| Arquivo | O quê |
|---|---|
| `validate.deletion.yml` | cópia com a deleção LIMPA (candidata da W4b) |
| `validate.deletion.measure.yml` | a de cima **+** a branch em `on.push.branches` (MEASURE-ONLY) |

**Execução das 3 corridas = CERIMÔNIA da W4** (rails r15/r16; os scripts de cerimônia da W4 (§9) foram
retirados — ver a errata do §4). Passos que a cerimônia executa, sob sentinel assinado:

0. ANTES de trocar de commit (rail r17: o `.txt` não existe em `ba15c71` e some do working tree
   no `switch`): `git show <SHA-deste-land>:.claude/plans/PLAN-186/w4/validate.deletion.measure.yml.txt > /tmp/w4a-measure.yml`.
1. `git switch -c plan186/w4a-validate-deletion-s341 ba15c718f8cb1ca37e8b909ddb321aa5bf78b1a9`
   (o commit dos 3 baselines do §6 — é o que garante comparabilidade); `cp /tmp/w4a-measure.yml
   .github/workflows/validate.yml`; commit; push. O nome da branch é o MESMO que o `on.push.branches`
   da cópia (`…-s341`).
2. Esperar cada run TERMINAR (`gh run watch <id>`) antes do marker-commit seguinte
   (`.claude/plans/PLAN-186/w4/.measure-run-2`, `-3`): `concurrency.cancel-in-progress` por
   ref cancela runs consecutivos — o «cancelled» que este repo já confundiu com timeout.
3. Para cada run e para os 3 baselines POR ID (`33709753629`, `33656365016`, `33630753334` —
   nunca «os últimos de main»): `gh run view <id> --json jobs,startedAt,updatedAt` (rail r23: `completedAt` NÃO é campo de
   run no gh 2.98.0 — é campo de JOB; o wall do RUN é `startedAt`→`updatedAt`, ou
   `gh api repos/<owner>/<repo>/actions/runs/<id>` com `run_started_at`→`updated_at`); minutos
   por label de runner somando `startedAt`→`completedAt` de cada JOB (`Ceo` vs `ubuntu-latest`).
   Preencher o §7.
4. A branch é descartável e NÃO se mergeia. **A W4b NÃO landa o snapshot** (rail r24 P2): as cópias
   `.txt` estão ancoradas em `ba15c71` e copiá-las sobre um `validate.yml` que mudou reverteria gates
   intermediários numa superfície guardada (`AGENTS.md:86-91,110`). A W4b RE-DERIVA a deleção do
   arquivo VIVO no LAND (anchor-exact, como toda cerimônia deste repo) e aborta se o sha do vivo
   diferir do que a derivação espera.
5. **Required check (rail r24, P1):** `docs/BRANCH-PROTECTION.md:101-105` documenta UM check
   obrigatório do Validate; após a deleção as suítes de hooks/scripts rodam SÓ em
   `hook-tests-python-matrix`, que não é o check obrigatório. A W4b deve adicionar
   `hook-tests-python-matrix (3.9)` e `(3.12)` aos required checks NO MESMO patch — senão uma
   matriz vermelha coexiste com um Validate «verde» e o merge passa.
