# Pacote E — `upgrade.sh` deriva o roster de hooks do template

> S329 (2026-08-26). Alvo canônico: `scripts/upgrade.sh`
> (`_merge_lifecycle_hooks_into_settings`, `:2497` pré-cura, chamada em `:3434`).
> Achado de origem: `.claude/plans/PLAN-179/s328-ceremony-D/FINDING-upgrade-lifecycle-hooks-S328.md`
> (S328, rail codex rodada 3 do pacote D).
> Trabalho feito em sombra (`git clone --local` de `b07be9b`); nada tocado no repo vivo.

## 1. O que mudou, em cinco linhas

| Dimensão | Antes (pré-S329) | Depois |
|---|---|---|
| **Fonte** | roster LITERAL de 6 registros dentro do programa `jq`, mais os mesmos 6 repetidos em prosa para o `--dry-run` | `$SOURCE_DIR/templates/settings/settings.base.json` — o template do checkout que EXECUTA o upgrade (mesma resolução que `_migrate_settings_baseline` já usa para o cap do pair-rail). Nunca `$TARGET`. |
| **Semântica** | os 6 eram RE-CANONICALIZADOS (filtra o pré-existente, re-appenda o bloco canônico) — edição do adopter era silenciosamente substituída | ADITIVA: ausente ⇒ appenda o bloco do template; presente ⇒ **preserva byte-idêntico**. Nada presente é reescrito. |
| **Chave de identidade** | `test("check_foo\\.py")` — substring, sem âncora | todo token `<nome>.py` do `hooks[].command`, casado como token INTEIRO (a classe de caracteres para em `/`, então um path rende o basename; o lookahead impede `check_x.py` casar dentro de `check_xy.py` / `check_xy.python`). Bloco sem `.py` (o `echo` inline do `PostToolUse\|Agent`) é chaveado pelo COMANDO inteiro. Um bloco presente conta como registrado quando TODAS as suas chaves já existem naquele evento. |
| **`--dry-run`** | loop `for pair in "PreCompact:…" …` — uma SEGUNDA lista, mantida à mão | mesmo programa `jq`, `--arg mode report`: o anúncio não pode divergir da escrita porque é a mesma redução. |
| **Atomicidade** | tempfile no mesmo dir + `[[ -s ]]` + `mv` | idem, mais validação `jq -e 'type=="object" and (.hooks\|type)=="object"'` do resultado ANTES do `mv`; e o arquivo **só é aberto para escrita quando falta alguma coisa** (re-run byte-idêntico — mesmo oráculo de idempotência da migração T5.4). |

## 2. Antes/depois por registro

Com o adopter partindo de `{"hooks": {}}` (o pior caso de adopter histórico):

| Evento / hook | Pré-cura registrava? | Pós-cura |
|---|---|---|
| `PreCompact` / `check_precompact_continuity.py` | sim (literal) | sim (derivado) |
| `PostCompact` / `check_postcompact_reinject.py` | sim (literal) | sim (derivado) |
| `ConfigChange` / `check_config_change.py` | sim (literal) | sim (derivado) |
| `SubagentStart` / `check_subagent_start.py` | sim (literal) | sim (derivado) |
| `Setup` (matcher `init`) / `check_setup_verification.py` | sim (literal) | sim (derivado) |
| `SessionStart` (matcher `compact`) / `check_compact_pinning.py` | sim (literal) | sim (derivado) |
| **`PreToolUse` / `check_ledger_checkpoint.py`** | **NÃO — o achado** | **sim** |
| os outros **40** registros do template (18 `PreToolUse`, 13 `PostToolUse`, `Stop` ×4, …) | NÃO | sim |

O template enumera **47** registros; o merge derivado entrega os 47.
Medido: E.2d/E.2g do e2e — nenhum faltando, nenhum inventado.

## 3. Dois achados medidos durante a implementação (não previstos no briefing)

### 3.1 As cópias literais já tinham APODRECIDO — e o upgrade estragava adopters corretos

Extraindo os 6 blocos literais de `git show HEAD:scripts/upgrade.sh` e comparando
com o template, campo a campo: **5 dos 6 DIVERGIAM** (todos no `_comment`;
só `Setup` batia). Como o `_reg` pré-cura RE-CANONICALIZAVA, a sequência real em
campo era:

1. `install.sh` entrega o template ⇒ adopter fica com o `_comment` CORRENTE;
2. o primeiro `upgrade.sh` sobrescreve 5 desses blocos com a cópia ESTAGNADA de dentro do upgrader.

Ou seja, a segunda declaração não era só redundante — era regressiva. É a
justificativa mais forte para a semântica aditiva: quem já está registrado não
é reescrito. Guardado como `E.9` do e2e (informativo; degrada para SKIP quando
`HEAD` já contém a cura).

### 3.2 O fail-safe pré-existente era grosso demais: UM evento estranho desligava TODO o merge

O e2e (`E.8`) plantou `.hooks.SubagentStart = {"not":"an array"}` e a primeira
versão da minha cura **falhou** — `jq` levanta ao fatiar um objeto, o `jq`
inteiro saía não-zero, e o wrapper tratava isso como "settings malformado" ⇒
`return 0` sem registrar NADA. O RED control mostrou que **a versão pré-cura tem
o mesmo defeito** (`test_a_non_array_event_value_...` vermelho contra `HEAD`),
então não é regressão minha, é uma classe pré-existente que a cura agora fecha.

Cura: `_cmds`/`_keys` aceitam apenas formas PROVADAS (object / array / string) e
rendem zero chaves para qualquer outra — mais um `select((.value|type)=="array")`
na lista de relatório. Fuzz de 8 formas hostis (evento não-array, blocos `1`/`"x"`,
`hooks` objeto, `command` numérico, `hooks:[null]`, `hooks:[]`, `hooks:null`, `{}`):
`rc=0` nas 8, tanto em `report` quanto em `apply`. Um evento estranho é
PRESERVADO e NOMEADO em stderr; os outros 46 registros seguem.

## 4. Testes

### e2e (bash) — `scripts/tests/test-upgrade-lifecycle-hooks-derived.sh`

```
$ bash scripts/tests/test-upgrade-lifecycle-hooks-derived.sh
RESULT: 51 passed, 0 failed          # 29 (r1) -> 36 (r2) -> 43 (§8) -> 51 (§9)
# 854 s de wall SOLO (e 1233 s com uma segunda lane de e2e rodando junto — os
# dois medidos, spread de 45%): 15 invocações de upgrade (13 reais + 2 --dry-run)
# e 11 adopters (1 install real de ~18 s, 10 cópias do cache).
```

Cobre, com install e upgrade REAIS: E.1 fixture não-vacuosa · E.2 adopter
strippado (4 formas diferentes: `.py` em evento cheio, `.py` com irmãos, EVENTO
inteiro ausente, bloco inline sem `.py`) volta completo · E.6 `--dry-run` nomeia
e não escreve · E.7 edição do adopter (`timeout=4242`) preservada e não duplicada ·
E.5 segundo upgrade byte-idêntico · **E.3 RED control** (upgrader pré-cura de
`git HEAD` contra o MESMO fixture deixa `check_ledger_checkpoint.py`
desregistrado — 2 registros faltando contra 0 do curado) · **E.4 controle
POSITIVO** (hook sintético `check_zz_synthetic_e4.py`, inexistente em
`upgrade.sh`, plantado só no template de uma cópia da árvore-fonte, é
registrado; e a árvore NÃO modificada não o registra) · E.8 fail-safe ·
E.9 a medição do §3.1.

Vermelho contra o vivo, como pedido — o e2e roda o pré-cura ele mesmo (E.3),
que é a mesma prova sem depender de eu editar o repo principal:

```
  ok   E.3a the pre-cure upgrader leaves check_ledger_checkpoint.py UNREGISTERED — the S328 finding reproduces
  ok   E.3b the pre-cure upgrader leaves 2 template registration(s) missing (the cured one leaves 0)
```

### unit (pytest) — `.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py`

```
$ python3 -m pytest .claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py -q
49 passed in 6.50s      # 23 (r1) -> 33 (r2) -> 40 (§8) -> 49 (§9)
                        # (+8 TestExplicitFalsyIsNotAbsent, +2 TestDuplicateOracle,
                        #  +11 TestTemplateMustBeStructurallyValid, +5 TestPreservedIsNotComplete)
```

**Por que dirige a FUNÇÃO e não o programa `jq` isolado:** o corpo é extraído do
`upgrade.sh` shipado por âncora (`^_merge_lifecycle_hooks_into_settings() {$` ..
`^}$` — o mesmo idioma que `test-upgrade-historical-adopter.sh` usa para
`_up_tmpbase`) e sourceado num harness bash com `TARGET`/`SOURCE_DIR`/`BAK_DIR`/
`DRY_RUN`/`SETTINGS_MERGE` postos e `_up_record_op` stubado. As guardas
fail-open, a escrita atômica, o ramo `--dry-run` e as mensagens que o adopter LÊ
vivem no wrapper — e o único defeito real desta wave (§3.2) morava exatamente
ali. Um harness só-`jq` teria passado verde por cima dele. O `SOURCE_DIR` de
scratch também deixa cada variante de template custar milissegundos.

Contém o guard anti-rot `TestNoSecondRoster::test_the_function_names_no_hook_filenames`:
**vermelho se qualquer nome de hook voltar a aparecer dentro da função.** É a
regra que impede a classe de renascer.

**RED control do pytest** (mirror root com o `upgrade.sh` de `git HEAD`, sem
tocar na sombra — sha256 do arquivo curado conferido idêntico antes e depois):

```
17 failed, 6 passed in 0.64s
```

Entre os vermelhos: `test_the_function_names_no_hook_filenames`
(`['_name.py', 'check_compact_pinning.py', …] != []`),
`test_every_template_registration_lands_on_an_empty_settings` (6 de 47),
`test_the_function_reads_the_template_from_the_source_checkout`,
`test_a_non_array_event_value_...` (o §3.2). Os 6 verdes contra o pré-cura são
honestos: são asserções que valem nos dois mundos (ex.: preservação de um
`check_x.py` que não está entre os seis) — a discriminação delas vem do e2e,
que usa o template REAL.

### Gates de corpus (rodados DEPOIS da última edição, por CLAUDE.md §4)

> Esta tabela é o registro da **rodada 1**. Os mesmos gates foram re-rodados
> depois das curas da rodada 2 — resultados no quadro do §7, mais o parse do
> YAML do `smoke-install.yml`, que só entrou no escopo na rodada 2.

| Gate | Resultado |
|---|---|
| `bash -n scripts/upgrade.sh` | OK |
| `shellcheck -S warning scripts/upgrade.sh` | rc=0 (nota: o step do `validate.yml` varre só `.claude/scripts` + `.claude/hooks`; `scripts/` fica FORA — rodei à mão) |
| `bash -n scripts/tests/test-upgrade-lifecycle-hooks-derived.sh` | OK |
| `shellcheck -S warning scripts/tests/…derived.sh` | rc=0 |
| `python3 .claude/scripts/check-test-env-hygiene.py` | OK, 0 violações novas (**pegou uma real**: `TestNoSecondRoster` nascera `unittest.TestCase`; curado para `TestEnvContext`) |
| `python3 .claude/scripts/check-ceremony-script.py` | blocking não-waivado: 0 |

## 5. Questões abertas para o Owner

**OQ-E1 (a que decide o escopo) — derivar TODAS as 47 entradas muda quem manda
no roster do adopter.** O briefing do CEO pediu "todas as entradas de
`.hooks[*][]`, não só as seis", e é isso que está implementado: é a única
semântica que fecha a classe (o adopter instalado em v1.0.0 não recebe HOJE
nenhum hook posterior que não seja um dos seis). O efeito colateral: quem
REMOVEU um hook de propósito o recebe de volta a cada upgrade. Hoje o escape é
só o `--no-settings-merge`, que é tudo-ou-nada.
*Opção conservadora, se o Owner quiser:* uma denylist por nome no
`settings.json` do adopter (ex.: `"_ceoOptOutHooks": ["check_x.py"]`) respeitada
pelo merge. Não implementei — inventa superfície de configuração e o Owner não
pediu.

**OQ-E2 — posição de inserção.** Blocos re-adicionados entram no FIM do array do
evento; no template alguns estão no meio (o `echo` inline do `PostToolUse` é o
4º de 13). O código pré-cura fazia o mesmo (`+ [$entry]`), e o harness não
documenta ordem dentro de um evento. Se ordem for load-bearing em algum evento,
a inserção deveria espelhar o índice do template. Conservador = manter append
(comportamento idêntico ao que já rodava em campo).

**OQ-E3 — o nome da função ficou estreito.** `_merge_lifecycle_hooks_into_settings`
já não registra só hooks de "ciclo de vida". Mantive o nome: renomear toca o
call-site e a superfície canônica sem comprar nada, e a mesma função aparece em
duas cópias staged (`PLAN-169/staged-w3/`, `PLAN-180/staged-s313/`) que
divergiriam de qualquer jeito. Anotado no comentário do código.

**OQ-E4 — RESOLVIDA na rodada 2 (§7.2): o wiring entrou neste mesmo patch.**
O texto abaixo é o registro de como a questão foi levantada; a cura está no §7.

**OQ-E4 (texto original) — ⛔ O TESTE e2e NASCE DESLIGADO, e isso é bloqueante.**
`.github/workflows/smoke-install.yml` está FORA do meu FILE ASSIGNMENT, e é o
único lugar onde `scripts/tests/*.sh` roda. O comentário do próprio workflow
(`:31`, `:47`, `:82`) diz a regra: *"unwired = no test"*. A cerimônia PRECISA
adicionar, no mesmo patch:

- em `paths:` (as duas listas, `push` e `pull_request`):
  `- "scripts/tests/test-upgrade-lifecycle-hooks-derived.sh"`
  e `- "templates/settings/settings.base.json"` (uma mudança no template é
  exatamente o que este teste existe para vigiar);
- um step no molde do vizinho (o de `test-upgrade-historical-adopter.sh`,
  `:570-574`), `if: always()`, `set -euo pipefail`, `bash scripts/tests/test-upgrade-lifecycle-hooks-derived.sh`.

Custo medido: ~5 min 40 s locais; o job já tem `timeout-minutes` folgado, mas
vale conferir a margem. Sem isso a cura entra sem vigilância e a classe volta.

**OQ-E5 — `--slurpfile` exige jq ≥ 1.5** (2015). O código já dependia de `jq`;
isto acrescenta uma FLAG. Se algum adopter alvo puder ter jq mais velho, o
fallback portátil é `jq -s '.[0] as $a | .[1] as $t | …' settings template`.
Medido aqui em `jq-1.7.1`.

**OQ-E6 — quem REPARA um registro que derivou?** A semântica aditiva move o
reparo para fora do upgrader (INV-4: edição do adopter é preservada). Escrevi
"é papel do `doctor.sh`" no comentário do código — **mas verifiquei e o
`doctor.sh` hoje NÃO repara registros de hook**; ele só confere o *timeout* do
`check_pair_rail.py` (`doctor.sh:930-969`). Então, hoje, um registro que o
adopter deformou fica deformado. Não é regressão (pré-cura só re-canonicalizava
6 de 47), mas a frase do comentário descreve um destino, não um mecanismo
existente. Se o Owner quiser fechar: wave própria no `doctor.sh`, reusando esta
mesma derivação.

## 6. O que o rail codex provavelmente vai levantar

1. **`_up_record_op` agora dispara mesmo quando o merge é no-op** — mantive a
   posição exata de hoje (antes do ramo `--dry-run`), como o briefing pediu
   ("como hoje"), para não mexer no oráculo de `test-upgrade-dryrun-identity.sh`.
   Defensável, mas é uma assimetria: registra uma operação que pode não escrever.
2. **`$_pending` cresce sem limite** — num adopter muito antigo o log lista as
   47 linhas. É deliberado (a regra do dry-run é o adopter poder revisar), mas
   alguém vai pedir um cap.
3. **A chave de um bloco inline é o comando inteiro** — um adopter que mudou um
   espaço no `echo` inline recebe um SEGUNDO bloco. Não achei jeito honesto de
   evitar sem normalizar o comando (e normalizar arrisca colidir dois blocos
   distintos). Registrado aqui em vez de escondido.
4. **`E.9` compara contra `git HEAD`** e vira SKIP depois que a cura landar —
   por desenho (é medição histórica, não invariante), mas é um verde que muda de
   significado com o tempo, e a classe "instrumento verde cuja PERGUNTA
   envelheceu" é conhecida deste repo.
5. **O e2e depende de `git show HEAD:scripts/upgrade.sh`** (E.3): num checkout
   raso isso ainda funciona (é o HEAD, não uma geração antiga), mas se a
   cerimônia landar a cura, `HEAD` passa a conter a cura e E.3 vira o SKIP
   explícito com instrução de re-armar. Está tratado, mas é uma manutenção
   futura real.

---

## 7. Rail round 1 — achados e curas

Rodada 1 do pair-rail codex sobre a sombra (registro em
`rail-round-1.md`): **REJECT, 0 P1, 3 P2**. Os três eram reais e estão
curados abaixo. Nenhum arquivo canônico fora do FILE ASSIGNMENT foi tocado;
a superfície cresceu de 4 para 5 paths (entrou `.github/workflows/smoke-install.yml`,
que é a cura do achado 2 e estava explicitamente fora do meu escopo na rodada 1
— era a OQ-E4).

Estado depois das curas:

| Gate | Rodada 1 | Rodada 2 |
|---|---|---|
| e2e (`test-upgrade-lifecycle-hooks-derived.sh`) | 29 passed / 0 failed | **36 passed / 0 failed**, 535 s (43 / 0 no §8; **51 / 0** no §9) |
| unit (`test_upgrade_lifecycle_hooks_derived.py`) | 23 passed | **33 passed**, 3,15 s (40 no §8; **49** no §9) |
| `bash -n` (upgrade + e2e) | OK | OK |
| `shellcheck -S warning` (upgrade + e2e) | rc=0 | rc=0 |
| YAML do `smoke-install.yml` | — (não estava no escopo) | parse OK, 24 steps, listas idênticas |
| `check-test-env-hygiene.py` | OK | OK (337 flagged, todos allowlisted) |
| `check-ceremony-script.py` | blocking 0 | blocking 0 |

### 7.1 [P2] Um container falsy EXPLÍCITO era lido como ausência

**Achado.** `scripts/upgrade.sh:~2600-2608`. As duas perguntas de presença
usavam o idioma óbvio de jq — `.hooks == null` e `.hooks[$ev] // []` — e esse
idioma **não distingue "a chave nunca foi escrita" de "o adopter escreveu
`null`/`false` de propósito"**: `null // []` e `false // []` rendem os dois
`[]`. Consequência medida: um adopter que tinha esvaziado `.hooks`
deliberadamente recebia os 47 registros de volta, em contradição direta com o
parágrafo de contrato logo acima da função ("uma estrutura que não entendemos é
PRESERVADA e NOMEADA, nunca coagida").

**Cura.** Toda pergunta de presença passou a ser `has(...)` sobre o
**container**, nunca um default `//` sobre o valor — no nível do documento, no
nível de `.hooks` e no nível do evento. O tipo observado é NOMEADO em stderr.

Fechou junto uma variante que o rail não citou e que é da mesma família, um
nível ACIMA de `.hooks`: um `settings.json` cujo documento inteiro é `null`.
Pré-cura, `null.hooks` rende `null`, `$ah` virava `{}` e o documento era
SUBSTITUÍDO — em silêncio. Medido (`nulldoc.sh`):

```
live    file=[{"hooks":{"PreCompact":[{"_comment":"PLAN-135W2H1(AD]  stderr=[]
cured   file=[null]  stderr=[settings-merge skipped — .claude/settings.json is not a JSON object (found: null); PRESE…]
```

Um topo não-objeto de outro tipo (`[1,2,3]`) caía antes no ramo de raise do jq e
saía como `"malformed settings.json?"`; agora os dois são
`SKIP-ALL document <tipo>`, nomeados com o tipo encontrado.

**Decisão de redação.** A primeira versão da mensagem era `is <tipo>, not an
array`, e isso **quebrou dois consumidores** que casavam a frase antiga
(`test_a_non_array_event_value_...` e o `grep` de `E.8b`). O diagnóstico entrou
como sufixo `(found: <tipo>)` justamente para não aposentar em silêncio a
redação que testes e runbooks já casam.

**Prova — controle vermelho em três textos** (`e10-redcontrol.sh`, no
scratchpad; dirige a MESMA função extraída de cada texto):

```
                        live (= HEAD)          staged (1ª passada)    curado
hooks-explicit-null     OVERWRITTEN  SILENT    OVERWRITTEN  SILENT    PRESERVED  named-on-stderr
hooks-explicit-false    OVERWRITTEN  SILENT    PRESERVED    named     PRESERVED  named-on-stderr
event-explicit-null     array(len=1) OVERWR.   array(len=1) OVERWR.   null       PRESERVED
event-explicit-false    array(len=1) OVERWR.   array(len=1) OVERWR.   boolean    PRESERVED
event-ABSENT   (ctrl)   registra              registra               registra
hooks-ABSENT   (ctrl)   registra              registra               registra
```

`live` é byte-idêntico ao `HEAD` da sombra — verificado por hash, não assumido:
`shasum -a 256` dá `54cc2af…` para os dois (o repo vivo está limpo nesse path).
As duas últimas linhas são o **controle contra a sobre-correção**: a ausência
continua registrando nos três textos, então a cura mudou o comportamento
*apenas* para valores presentes-e-falsy.

Honestidade sobre o achado: `hooks-explicit-false` **já estava correto na 1ª
passada** (o `type != "object"` do container pega `false`). O defeito real da 1ª
passada era o `null` no container e o `null`/`false` no evento. O rail nomeou a
classe certa e uma instância a mais do que existia naquele texto — a instância a
mais existe no código VIVO.

**Testes novos:** `TestExplicitFalsyIsNotAbsent` (8 casos, incluindo os dois
controles de ausência e o `[]` que é container legítimo) e `E.10a–E.10e` no e2e,
com install+upgrade reais. `E.10a` é o anúncio em `--dry-run` do container
preservado, que o rail pediu explicitamente.

O `E.10d` acabou medindo mais do que eu tinha desenhado, e a mais forte:
`_migrate_settings_baseline` (T5.4) roda LOGO DEPOIS do merge (`:3585` e
`:3590`) e também escreve `settings.json`. Como a asserção é byte-identidade do
ARQUIVO após um upgrade inteiro, o verde diz que nem o merge nem a migração T5.4
tocam um `settings.json` com `.hooks` explicitamente `null` — não só a função
que eu curei.

### 7.2 [P2] O e2e nascia CI-dark (era a OQ-E4)

**Achado.** Nem step nem entrada nas duas listas `paths:` de
`smoke-install.yml` — e esse workflow é o único lugar onde `scripts/tests/*.sh`
roda. `E.1–E.10` nunca executariam. É a regra que o próprio arquivo escreve em
`:30-34`: *unwired = no test*, e esta seria a **quarta** instância registrada
nele.

**Cura.** Entrada nas DUAS listas + um step no molde exato do vizinho mais
próximo (`test-upgrade-historical-adopter.sh`): mesmo job, `if: always()`,
`set -euo pipefail`, `bash scripts/tests/…`, sem `continue-on-error`. Não
acrescentei `templates/settings/settings.base.json` às listas como a OQ-E4
propunha: `templates/**` já está nas duas e cobre o template — uma entrada
redundante seria uma segunda declaração da mesma verdade, que é exatamente a
classe que esta wave existe para remover.

**Prova** (paridade das listas medida, não conferida a olho — o próprio arquivo
manda «KEEP IDENTICAL» e as duas já tinham divergido uma vez, no PLAN-166 F4):

```
python-yaml: parsed OK; steps=24
new step present: True
pull_request paths=37  push paths=37
sets identical: True     diff pr-only: []     diff push-only: []
target in pr: True   in push: True
templates/** present nas DUAS: True   (settings.base.json literal: False, por decisão)
```

**`timeout-minutes` 68 → 111** (passou por 96 e 101 conforme as pernas cresceram;
a história e o porquê da correção estão no §9.5). Dimensionado pelo método que o
próprio arquivo escreve: 854 s locais SOLO × fator 2–3× de runner = 28–43 min de
CI novos; +43 pega o topo da faixa e soma a margem anti-flake. A assimetria que justifica arredondar
para cima: super-dimensionar não custa nada num run verde, sub-dimensionar
aparece como `cancelled` num step inocente. Está escrito no comentário que o
primeiro run REAL é o número que deve substituir esta estimativa.

**Correção de uma afirmação minha:** o primeiro rascunho do comentário do step
dizia que o teste depende do `Deepen git history`. É **falso** — `E.3`/`E.9`
leem `git show HEAD:…`, que um checkout `depth-1` satisfaz. O comentário
final diz isso, e diz também que `E.3` se auto-declara EXPIRADO assim que a cura
estiver em `HEAD` (o §6.5 previu; agora está escrito onde o próximo leitor olha).

### 7.3 [P2] A asserção de duplicatas era estruturalmente incapaz de falhar

**Achado.** `E.2h` fazia `sort … | uniq -d` sobre a saída de `_keyset`, que já
emitia `sorted(set(out))`. O fluxo chegava desduplicado, então `uniq -d` era
sempre vazio. O mesmo ponto cego no unit (`len([k for k in _keyset(…) if k == X]) == 1`
é ≤ 1 por construção).

**Cura.** Duas funções com nomes diferentes, nos dois arquivos: `_keyset`
(pergunta "falta ou sobra algo?", precisa de conjunto — é o que `comm` consome)
e `_keybag` (pergunta "duplicou?", preserva multiplicidade). Separadas de
propósito em vez de um parâmetro com default, para que o próximo chamador tenha
de ESCOLHER a pergunta.

**Prova — controle positivo permanente, não uma verificação de uma vez.**
`E.2i` planta uma duplicata real no fixture pós-upgrade e exige que o oráculo
novo a veja; `E.2i-b` exige que o oráculo antigo continue cego à MESMA
duplicata — é a medição que condena a forma anterior, e ela fica no arquivo:

```
  ok   E.2h no registration is duplicated (counted with multiplicity — 47 keys)
  ok   E.2i a planted duplicate registration IS reported by the multiplicity oracle — E.2h can fail
  ok   E.2i-b the SET oracle stays silent on the very same planted duplicate — which is why E.2h could never fail before (rail round 1, P2)
```

No unit, `TestDuplicateOracle` faz o par equivalente. Medido antes: o template
tem 47 chaves e 47 distintas, então a asserção de multiplicidade não tem
falso-positivo legítimo contra o artefato real.

### 7.4 Dois defeitos que eu mesmo introduzi — e quem os achou

**(a) Ordem do fixture do `E.10`, achado antes de rodar.**

O fixture original do `E.10` plantava `.hooks.PreCompact = null` **antes** de
`_strip_four`, e `_strip_four` contém `del(.hooks.PreCompact)` — o `null` era
apagado logo em seguida e o teste teria medido o caso AUSENTE com o nome do caso
explícito. Ordem invertida e, nos dois fixtures do `E.10`, um `scaffold` que
verifica que o plantio é o que a asserção assume (`has(...)` + valor `null`).
Sem esse guarda, um `jq` que falhasse deixaria um install COMPLETO, cujo merge é
legitimamente no-op — e o `E.10d` (byte-identidade) passaria medindo nada.

**(b) O `E.2i` acusava o ORÁCULO por um fixture que não disparou — achado PELO
red control do §7.5.** O plantio original duplicava o bloco do
`check_ledger_checkpoint` selecionando-o por nome. Isso acoplou o controle ao
resultado do MERGE: rodado contra o upgrader vivo, que nunca registra esse hook,
o seletor não casava nada, nenhuma duplicata era plantada — e o `E.2i` imprimia
*"a planted duplicate was NOT reported — E.2h is still vacuous"*, culpando o
oráculo por um fixture inerte. O `[ -s "$DUP_FIX" ]` que eu tinha posto como
guarda não pega: a saída do `jq` é o `settings.json` inteiro, nunca vazia.

Cura: o plantio duplica `PreToolUse[0]` (existe em qualquer adopter instalado,
independente do merge) e um guarda compara a CONTAGEM de chaves antes/depois —
se não cresceu, sai `E.2i-SCAFFOLD`, com a frase dizendo explicitamente que o
silêncio dele **não é** evidência sobre o `E.2h`. É a diferença entre "o
instrumento mediu e não achou" e "o instrumento não mediu", que era exatamente o
que a mensagem antiga apagava.

Vale registrar de onde veio o achado: **nenhum dos gates da rodada 2 o pegou** —
os 36 verdes da árvore curada incluíam esse `E.2i` acoplado. Quem o expôs foi
rodar o instrumento contra o código NÃO curado, que é a única configuração em
que o fixture falha. Um controle vermelho serve para vigiar o produto; este
vigiou o próprio teste.

### 7.5 RED CONTROL da rodada 2 — os testes novos contra o upgrader VIVO

Uma asserção que passa nos dois mundos não prova nada. Montei uma árvore
espelho (`shadow-E-red`) com **os testes NOVOS** e o **`scripts/upgrade.sh`
VIVO** (`git checkout HEAD -- scripts` e depois só o arquivo de teste de volta;
sha `54cc2af…` conferido contra o repo vivo — os dois batem):

```
$ python3 -m pytest .claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py -q
25 failed, 8 passed in 1.45s          # contra o VIVO
                                       # (33 passed, 0 failed contra o curado)
```

Recorte da classe nova, que é a pergunta que importa:

```
$ python3 -m pytest … -k 'ExplicitFalsy or DuplicateOracle' -q
8 failed, 2 passed, 23 deselected
```

**Os 8 de `TestExplicitFalsyIsNotAbsent` falham contra o vivo e passam contra o
curado** — inclusive os dois controles de ausência, que falham por um motivo
DIFERENTE (o upgrader vivo só conhece os seis literais, então nem o caso ausente
ele registra). Os 2 de `TestDuplicateOracle` passam nos dois mundos, e isso está
certo: eles afirmam propriedades do ORÁCULO (`_keybag` vê a duplicata,
`_keyset` não), que são funções puras e não dependem do produto. Registro para
que ninguém leia esses dois verdes como evidência sobre o `upgrade.sh`.

Os outros 8 verdes contra o vivo são asserções que valem legitimamente nos dois
mundos (ex.: `test_an_adopter_edit_survives` — o pré-cura re-canonicalizava
apenas os SEIS, e `check_x.py` não é um deles). A discriminação delas vem do
e2e, que usa o template REAL.

**O e2e, na mesma montagem:**

```
$ bash scripts/tests/test-upgrade-lifecycle-hooks-derived.sh   # árvore CURADA
RESULT: 36 passed, 0 failed

$ bash scripts/tests/test-upgrade-lifecycle-hooks-derived.sh   # upgrade.sh VIVO
RESULT: 22 passed, 14 failed
```

As 14 que só o curado passa — a lista é o que este patch entrega:

```
  E.6a  --dry-run não anuncia check_ledger_checkpoint.py
  E.2d  registros ainda faltando depois do upgrade (2)
  E.2e  check_ledger_checkpoint.py segue desregistrado — O ACHADO da S328
  E.2f  o bloco inline sem .py não volta (a chave de identidade não cobre a forma)
  E.5b  o segundo run não reporta o no-op (o pré-cura reescreve sempre)
  E.4c  o hook SINTÉTICO do template não é registrado  ← o roster não é derivado
  E.4d  e o log nem o menciona
  E.8b  o evento estranho não é NOMEADO
  E.8c  o evento estranho ABORTA o merge inteiro (§3.2)
  E.10a --dry-run não nomeia o evento explicitamente null
  E.10b .hooks.PreCompact explicitamente null é SOBRESCRITO      ← achado do rail
  E.10c o evento null aborta o resto do merge
  E.10d o merge REESCREVE um settings.json com .hooks null       ← achado do rail
  E.10e o .hooks null não é nomeado
```

As **cinco** do `E.10` falham contra o vivo e passam contra o curado: a cura do
§7.1 tem controle vermelho e2e, não só o de função do `e10-redcontrol.sh`.

O `E.2h`/`E.2i` passam nos DOIS (47→48 chaves no curado, 45→46 no vermelho) —
correto e agora deliberado: depois da cura do §7.4(b) o plantio não depende mais
do merge, então o controle do oráculo mede o oráculo nas duas árvores. O `E.3`
também passa nas duas, porque nas duas ele replica `HEAD`, que é pré-cura em
ambas.

### 7.6 O que esta rodada NÃO fecha

1. **O `timeout-minutes` é dimensionado por medição LOCAL, não por p95 de CI.**
   Segui a doutrina que o próprio arquivo escreve (medir local, aplicar o fator
   2–3× de runner, somar margem anti-flake, nunca re-apertar por aritmética),
   mas nenhum run de CI deste step existe ainda. O primeiro run real é o dado
   que deve substituir esta estimativa.
2. **`E.3` e `E.9` expiram quando a cura entrar em `HEAD`** (§6.4/§6.5). Isso já
   era verdade na rodada 1; o que mudou é que agora está escrito no comentário
   do step do workflow, que é onde o próximo leitor procura.
3. **`$_pending` continua sem cap** (§6.2): um adopter muito antigo vê as 47
   linhas. Deliberado, mas alguém vai pedir um limite.
4. **OQ-E1 segue aberta** — derivar as 47 entradas muda quem manda no roster do
   adopter, e quem removeu um hook de propósito o recebe de volta. É decisão do
   Owner, não deste patch.
5. **`$tpl[0]` é assumido existir no programa jq.** Com `--slurpfile` sobre um
   arquivo vazio, `$tpl[0]` seria `null` e o `($tpl[0].hooks | type)` renderia
   `"null"` ⇒ `$th = null` ⇒ `SKIP-ALL template`. O caminho é inalcançável
   porque o wrapper valida o template com `jq -e` ANTES; registro aqui que a
   defesa é em profundidade e não acidental.
6. **O `_keybag` do e2e e o do unit são duas implementações da mesma derivação**
   — de propósito (o oráculo não importa o extrator da implementação, §4), mas
   é uma segunda cópia de uma REGRA, e a wave inteira é sobre segundas cópias.
   A diferença que a justifica: essas duas descrevem o ORÁCULO, não o produto,
   e divergir entre si faz um dos dois ficar vermelho — o modo de falha é
   visível, ao contrário do roster literal que esta wave removeu.

---

## 8. Rail round 2 — achado e cura

> O CEO pediu esta seção como «§7.4». Os slots 7.4–7.6 já estão ocupados por
> material da rodada 1 (defeitos meus, red control, residuais), então a rodada 2
> ganhou seção própria. É esta.

Rodada 2 do pair-rail codex sobre a sombra: **1 P1 + 1 P2**.

O **P1** («sem sentinel assinado pelo Owner para `scripts/upgrade.sh` e
`.github/`») é por construção — a sombra é revisada ANTES da cerimônia e o
sentinel é o próprio pacote E, em montagem. Instrução explícita do CEO: não agir
sobre ele. Registrado aqui só para que a leitura do registro do rail não sugira
um item pendente que não existe.

### 8.1 [P2] O guard do template parava em «`.hooks` é objeto»

**Achado.** `scripts/upgrade.sh:~2573`. O guard aceitava qualquer template cujo
`.hooks` fosse objeto, sem olhar o valor de cada evento. Se o valor de um evento
não é array, o `$te.value[]?` do programa erra de duas maneiras — e as duas são
**silenciosas**:

| valor do evento no template | o que `.[]?` faz | consequência |
|---|---|---|
| **objeto** | itera os VALORES do objeto | o que estiver sob aquelas chaves é entregue ao merge **como se fosse um bloco de hooks** e pode ser APPENDADO no `settings.json` do adopter |
| **escalar / `null` / `false`** | não rende nada (o `?` engole o erro) | o evento inteiro **some do roster, sem uma palavra** |

O segundo é a própria classe que esta wave existe para remover, uma camada
acima: registros que estão no template e nunca chegam ao adopter.

**Cura.** Um terceiro guard, ANTES de qualquer trabalho de merge: todo valor de
evento do template tem de ser array. Se algum não for, **nenhuma escrita**, e
cada ofensor é nomeado em stderr com o tipo encontrado
(`template event not an array: PreCompact (object)`).

**A assimetria é deliberada, e agora está escrita no contrato da função.** O
`settings.json` do adopter é entrada não-confiável e possivelmente editada à
mão: uma forma que não entendemos é PRESERVADA e NOMEADA **por evento**, e os
outros 46 registros seguem (é o que E.8/E.10 medem). O **template** é outra
coisa: é o artefato que DEFINE o roster, vem com o framework, e um template
malformado significa que não sabemos qual é a resposta certa. Não há merge
parcial a salvar — degradar para «funde os eventos que por acaso parseiam»
entregaria um roster truncado em silêncio, que é exatamente o bug desta wave.
Por isso o template é fail-CLOSED sobre o merge (e advisory sobre o upgrade,
por CLAUDE.md §5: o resto do upgrade segue).

**Prova — controle vermelho por MECANISMO** (`tpl-redcontrol.sh`, no scratchpad;
dirige a MESMA função extraída do texto da rodada 1 e do curado, e imprime o que
ATERRISSOU por chave de registro, não apenas «mudou/não mudou»):

```
object-valued event
   pre-cure  WROTE keys: PreToolUse:evil_smuggled.py    named-lines=0
   cured     UNCHANGED                                  named-lines=2
scalar-valued event
   pre-cure  WROTE keys: Stop:ok_stop.py                named-lines=0
   cured     UNCHANGED                                  named-lines=2
null-valued event
   pre-cure  WROTE keys: Stop:ok_stop.py                named-lines=0
   cured     UNCHANGED                                  named-lines=2
well-formed (control)
   pre-cure  WROTE keys: PreToolUse:check_ok.py         named-lines=0
   cured     WROTE keys: PreToolUse:check_ok.py         named-lines=0
```

Linha 1: o pré-cura registrou `evil_smuggled.py`, um hook que o template **nunca
declarou como bloco** — ele estava sob uma chave de um objeto, e o `.[]?` o
entregou como se fosse um. Linhas 2–3: o `PreToolUse` do template
simplesmente não aparece no resultado — sumiu calado; só o `Stop` (bem-formado)
entrou. Linha 4 é o controle contra a sobre-correção: um template válido segue
fundindo idêntico nos dois textos.

**Testes.** `TestTemplateMustBeStructurallyValid` (7 casos) e `E.11a–E.11f` no
e2e, com install+upgrade reais.

Três escolhas de teste que valem registro:

- **`test_a_scalar_valued_template_event_refuses_the_WHOLE_merge`** afirma que o
  irmão BEM-FORMADO (`Stop`) também não é fundido. Sem essa asserção, uma
  implementação que pulasse só o evento ruim passaria — e é justamente a
  degradação que produz roster truncado.
- **`test_the_shipped_template_passes_the_guard`** roda o critério do guard
  contra `templates/settings/settings.base.json` de verdade. Um guard que
  recusasse o artefato real quebraria todo upgrade; a asserção é barata e o
  modo de falha seria catastrófico.
- **`E.11f` é o controle ANTI-VACUIDADE do `E.11b`**: a byte-identidade do
  `E.11b` passaria de graça se aquele fixture não tivesse nada a registrar.
  O `E.11f` re-upgrada o MESMO adopter a partir da árvore não modificada e exige
  que o arquivo MUDE — é o que transforma «não mudou» em evidência de recusa em
  vez de evidência de fila vazia. Mesma lição que o §7.4(b) pagou.

### 8.2 Discriminação, medida nas duas árvores

```
                                     curado            upgrader VIVO
e2e                                  43 passed / 0     26 passed / 17 failed
unit                                 40 passed / 0     (ver §7.5)
```

Do `E.11`, **`E.11b`/`E.11c`/`E.11d` falham contra o vivo** — correto: o
upgrader vivo não lê o template, então escreve os seus 6 literais (o arquivo
muda) e não nomeia nada.

`E.11e` (o anti-smuggling) passa nas DUAS, e isso é honesto em vez de
tranquilizador: o upgrader vivo não consegue contrabandear porque não lê o
template de forma alguma. O risco de contrabando é específico do código
derivado-do-template da rodada 1 — por isso o controle que vale para ele é o
`tpl-redcontrol.sh` do §8.1, que dirige o texto da RODADA 1 e mostra o
`evil_smuggled.py` aterrissando. Um teste e2e contra o vivo não podia provar
isso, e dizer que provou seria falso.

Pela mesma razão eu **não** rodei o pytest da classe nova contra o texto da
rodada 1: o guard de bash deste repo (corretamente) recusa
`git checkout -- scripts/upgrade.sh` e `mv` sobre um path canônico, mesmo numa
árvore de scratch, e reformular o comando até passar seria contornar um guard,
não medir. A evidência por MECANISMO do §8.1 é mais forte de qualquer jeito:
mostra O QUE deu errado (`PreToolUse:evil_smuggled.py` registrado; `PreToolUse`
sumindo do roster), não só quantos testes ficaram vermelhos.

---

## 9. Rail round 3 — dois achados e curas

> O CEO pediu estas seções como «§7.5/§7.6». Esses slots são material da rodada
> 1 e o §8 já é a rodada 2, então a rodada 3 ganhou seção própria — esta.
> O P1 «sentinel assinado pelo Owner» repetiu pela terceira vez e continua
> sendo por construção (a sombra é revisada ANTES da cerimônia); ignorado por
> instrução explícita do CEO, registrado aqui só para não parecer pendência.

Os dois achados são a **mesma pergunta em dois lugares**: *onde mais este código
degrada em silêncio para um roster parcial?* O §8 fechou a porta do nível de
EVENTO; a rodada 3 achou a porta do nível de BLOCO e a porta do RELATÓRIO.

### 9.1 [P2] Um bloco malformado DENTRO de um array de evento válido

**Achado.** `scripts/upgrade.sh:~2681-2685`. O guard do §8 valida que o valor de
cada evento é array — e para aí. Um array **contendo** um bloco que a derivação
de chaves não identifica (`null`, `{}`, `{"hooks":[]}`, uma entrada sem
`.command` string) rende zero chaves, e o braço `($k|length) == 0` da redução
**PULAVA o bloco em silêncio** enquanto os irmãos bem-formados eram fundidos.
Roster parcial de novo, por uma porta diferente da que o §8 fechou — e contra a
regra tudo-ou-nada que o próprio §8 estabeleceu.

Medido antes de curar: as quatro formas passam pelo guard de evento como limpas
e todas rendem `[]` de chaves.

```
  block=null                            guard-says=CLEAN;  _keys=[]
  block={}                              guard-says=CLEAN;  _keys=[]
  block={"hooks":[]}                    guard-says=CLEAN;  _keys=[]
  block={"hooks":[{"type":"command"}]}  guard-says=CLEAN;  _keys=[]
```

**Cura.** O mesmo guard passou a validar **cada bloco** antes de a redução
começar: objeto, com `.hooks` array **não-vazio**, cujas entradas são todas
objetos com `.command` string **não-vazia**. Qualquer outra coisa nomeia
`evento[índice] (razão)` e **nada é escrito**. As duas classes saem do MESMO
`jq`, com prefixos `EVENT`/`BLOCK`, para não haver dois lugares onde a regra
mora — que é o defeito que esta wave inteira remove.

Escolhi ser ESTRITO no `.command` de toda entrada (e não «pelo menos uma»):
identidade parcial é pior que nenhuma, porque um bloco com conjunto de chaves
incompleto pode casar como «já registrado» e suprimir um registro real.

### 9.2 [P2] Um evento PRESERVADO era reportado como «tudo já presente»

**Achado.** `scripts/upgrade.sh:~2748-2750`. Com um evento preservado no adopter
(ex.: `PreCompact: null`) e todas as outras registrações presentes, `_adds`
fica em 0 — e o resumo lia isso como completude: *«every framework hook
registration in the template is ALREADY present»*. Não está: os hooks que o
template declara sob o evento preservado são **exatamente** os que faltam.

Isso é pior que não imprimir nada, porque é a linha que o adopter lê para se
tranquilizar. É a classe «instrumento verde cuja PERGUNTA envelheceu», dentro
da própria mensagem de saída.

**Cura.** O relatório agora conta eventos pulados separadamente e carrega, no
próprio `SKIP-EVENT`, as chaves que o template declara sob aquele evento. A
frase de completude ficou **reservada para `_skips == 0`**; caso contrário o
resultado é PARCIAL e NOMEIA o que ficou de fora, com a instrução de como
consertar. A mesma função (`_report_preserved`) imprime esse rodapé no
`--dry-run` e no apply — os dois não podem divergir porque são o mesmo código.

**Prova — controle vermelho por MECANISMO** (`r3-redcontrol.sh`; dirige a mesma
função extraída do texto da RODADA 2 e do curado):

```
=== P2 (a): bloco malformado dentro de um array de evento válido ===
  pre    registered=[bash h.sh check_good.py]  wrote=YES  named-blocks=0
  cured  registered=[]                          wrote=NO   named-blocks=2

=== P2 (b): evento preservado não pode virar «tudo presente» ===
  apply   pre    claims-complete=1  names-absent-hook=0  says-partial=0
  apply   cured  claims-complete=0  names-absent-hook=1  says-partial=2
  dry-run pre    claims-complete=1  names-absent-hook=0  says-partial=0
  dry-run cured  claims-complete=0  names-absent-hook=1  says-partial=2

=== CONTROL: template válido + adopter completo ===
  pre    output=OK: every framework hook registration in the template is already present
  cured  output=OK: every framework hook registration in the template is already present
```

Linha 1 do (a): o pré-cura registrou `check_good.py` e descartou calado os dois
blocos ruins — roster parcial, exatamente o achado. No (b), o pré-cura afirma
completude e nunca nomeia o hook ausente, nos dois modos.

O bloco CONTROL é o que impede a cura de virar «apague a frase»: com um adopter
genuinamente completo, a frase de completude continua saindo nos dois textos.
`E.13d` e `test_a_genuinely_complete_adopter_still_says_already_present` fazem
essa mesma pergunta permanentemente, no e2e e no unit.

**O que o adopter LÊ agora** (saída verbatim, template real, `.hooks.PreCompact`
posto como `null`) — porque o defeito era de MENSAGEM e uma contagem de testes
verdes não mostra se a mensagem presta:

```
==> Registering framework hooks into .claude/settings.json (derived from templates/settings/settings.base.json)
    NOTE: event 'PreCompact' in settings.json is not an array (found: null) — PRESERVED untouched, nothing registered under it
    PARTIAL: nothing to register outside the preserved event(s) — settings.json untouched
    PRESERVED: 1 event(s) in settings.json are not arrays and were left untouched, so these template hooks are NOT registered:
      NOT REGISTERED under PreCompact: check_precompact_continuity.py
    To register them, make those events arrays in .claude/settings.json and re-run the upgrade.
```

Cinco coisas que a versão anterior não dizia: qual evento, que tipo foi
encontrado, que o resultado é PARCIAL, **qual hook exatamente ficou de fora**, e
o que fazer a respeito. A anterior dizia «every framework hook registration in
the template is ALREADY present».

**Testes.** `TestTemplateMustBeStructurallyValid` foi de 7 para 11 casos (o
`subTest` cobre as 7 formas de bloco inválido, cada uma exigindo a razão
NOMEADA), nova classe `TestPreservedIsNotComplete` (5 casos), e `E.12a–E.12d` +
`E.13a–E.13d` no e2e.

Duas asserções que não são óbvias:

- **`E.12d`** exige que um bloco ruim sob `PreCompact` impeça também o registro
  de `PreToolUse`. É a afirmação tudo-ou-nada de verdade; sem ela, uma
  implementação que recusasse só o evento afetado passaria.
- **`test_the_shipped_template_passes_the_guard`** ganhou a metade de BLOCOS.
  Isso importa mais do que parece: o guard é fail-closed sobre o merge inteiro,
  então um único bloco malformado no template shipado pararia de registrar
  hooks para todos os adopters — e o modo de falha seria silencioso. Um segundo
  teste (`test_the_guard_accepts_the_shipped_template_end_to_end`) roda o guard
  DE VERDADE contra o artefato real, porque o primeiro re-implementa a regra e
  um oráculo que só se compara consigo mesmo não vigia nada.

### 9.3 Discriminação, medida nas duas árvores

```
                                     curado            upgrader VIVO
e2e                                  51 passed / 0     29 passed / 22 failed
unit                                 49 passed / 0     9 passed / 40 failed
unit, só as classes da rodada 3      16 passed / 0     1 passed / 15 failed
```

Do `E.12`/`E.13`, **`E.12b`, `E.12c`, `E.13b`, `E.13c` e `E.13d` falham contra o
vivo**. Duas passam nas duas árvores, e vale dizer POR QUÊ em vez de contar como
evidência:

- **`E.12d`** («nenhum outro evento foi fundido») passa no vivo porque o vivo
  não lê o template de forma alguma — o `check_ledger_checkpoint.py` não seria
  registrado de qualquer jeito. Ela discrimina contra o texto da RODADA 2, não
  contra o vivo; quem prova isso é a linha 1 do `r3-redcontrol.sh`.
- **`E.13a`** («a frase de completude NÃO foi impressa») passa no vivo pelo
  motivo trivial de que aquela frase é redação minha da rodada 1 e o vivo nunca
  a imprime. Sozinha ela não vale nada; o par que vale é `E.13b`/`E.13c`
  (nomeia o hook ausente, rotula PARCIAL) mais `E.13d`.
- **`E.13d`** falha no vivo, e isso está CERTO: o vivo não imprime a frase nem
  quando ela seria verdadeira, porque a frase não existe lá.

No unit, a única da rodada 3 que passa contra o vivo é
`test_the_shipped_template_passes_the_guard` — que é oráculo puro sobre o
artefato e não dirige a função. Honesto, e registrado para ninguém ler esse
verde como evidência sobre o `upgrade.sh`.

### 9.4 Residuais desta rodada

1. **A lista de hooks NÃO-REGISTRADOS reusa o `_disp`, que corta em 160 chars.**
   Um adopter que tenha posto `PreToolUse` (18 hooks no template) como não-array
   veria a lista truncada. O corte é MARCADO com `...`, então não é silencioso,
   e a mensagem diz como consertar — mas a informação some. Não aumentei o cap
   porque `_disp` é compartilhado com as linhas `ADD` e mexer nele mudaria a
   saída do caminho normal; se alguém quiser, a cura é um segundo formatador
   só para esta lista.
2. **`_report_preserved` é função aninhada**, definida a cada chamada do merge.
   Funciona (o extrator do unit ancora em `^}$` na coluna 0 e o fecho dela é
   indentado, então a extração continua pegando a função inteira — provado
   pelos 49 verdes), mas é um idioma que este arquivo não usava. Preferi isso a
   uma função de topo porque o rodapé depende de `$_skips`/`$_absent`, que são
   locais do merge: uma função de topo precisaria recebê-los por argumento ou
   lê-los como globais, e as duas alternativas são piores.
3. **A regra de bloco válido é ESTRITA** (toda entrada precisa de `.command`
   string não-vazia). Se algum dia o template legítimo precisar de uma entrada
   de `hooks[]` sem `command` — outro `type` que o harness venha a suportar —
   o guard recusa o merge inteiro para todos os adopters. É fail-closed por
   desenho, e `test_the_guard_accepts_the_shipped_template_end_to_end` é o
   canário que dispara ANTES de isso chegar em campo; mas é uma restrição sobre
   a evolução do template que vale estar escrita.


### 9.5 O `timeout-minutes` e uma medição contra-intuitiva

Valor final: **68 → 111**. Passou por 96 (rodada 1) e 101 (rodada 2) conforme as
pernas de e2e cresciam. A correção da rodada 3 não foi só «somou mais upgrades»
— foi um erro de MÉTODO que vale escrever:

| medição | condição | upgrades | valor derivado |
|---|---|---|---|
| 535 s | carga leve | 10 | 96 |
| 649 s | 2 lanes de e2e | 12 | 101 |
| **854 s** | **SOLO** | **15** | **111** |
| 1233 s | 2 lanes de e2e | 15 | (descartado — ver abaixo) |

O erro: eu tratei os números CONTENDIDOS como «limite superior seguro»,
seguindo o precedente dos blocos vizinhos do `smoke-install.yml`. Mas o 649 s
contendido da versão de 12 upgrades é **MENOR** que o 854 s SOLO da versão de 15
— então o «limite superior» estava abaixo do valor real e o 101 nasceu apertado.
Contenção e tamanho do teste são eixos independentes; misturá-los produz um
número que não é conservador nem honesto.

O que fiz: medi as DUAS condições no mesmo estado final (854 s solo, 1233 s com
duas lanes; spread de 45%), usei a solo como base para o fator 2–3× de runner, e
registrei a contendida como o spread OBSERVADO em vez de multiplicá-la de novo —
compor duas pessimismos daria 130 e o número perderia valor diagnóstico.

A lição em uma linha, escrita no comentário do workflow para o próximo leitor:
**uma medição sob contenção não é automaticamente a conservadora.**

## 10. Re-derivação por item sobre `cc00235` (S329, manhã de 27/08)

O pacote C (PLAN-185 W1+W2) landou primeiro (`cc00235`) e tocou dois dos cinco
paths deste pacote — `scripts/upgrade.sh` e `.github/workflows/smoke-install.yml`.
O guard de drift do `finalize-E.sh` abortou corretamente («path(s) do pacote
mudaram no HEAD vivo depois que a sombra foi criada»). A cura foi a que o próprio
guard prescreve — re-derivar a sombra POR ITEM sobre o conteúdo novo — e não
forçar a cópia:

- **`scripts/upgrade.sh`** — rebase limpo. Os hunks de C (3676–3865: consumo de
  `_wbm_github_handle_ok` e `_wbm_nlink`) e os de E (2458–2848:
  `_merge_lifecycle_hooks_into_settings`) são disjuntos. O diff desta sombra
  contra `cc00235` mostra EXATAMENTE os dois hunks de E (+366 / −94, os mesmos
  números da rodada 5), e as 10 referências que C introduziu continuam
  presentes no arquivo composto. Nenhuma linha de E mudou.
- **`.github/workflows/smoke-install.yml`** — os dois pacotes adicionam nos
  MESMOS quatro lugares. União consciente, C primeiro (já vivo) e E depois: as
  duas listas de `paths:` carregam os dois e2e (3 referências cada, como o V2c
  de C e o 4f/V4 de E exigem); os dois steps coexistem, o de E logo abaixo do
  de C (o comentário de E passa de «four steps above» para «five»); e o
  `timeout-minutes` é COMPOSTO — C levou 68 → 83 (+15) e E soma os seus +43
  sobre a base NOVA: **126**, não 111. Tomar o maior dos dois valores (111)
  sub-dimensionaria o job exatamente pelo step de C — a classe «`cancelled`
  num passo inocente» que o próprio arquivo documenta. O bloco de comentário
  do timeout registra a composição.
- **`DESIGN-E.md`** — add/add contra o snapshot intermediário commitado no vivo
  (228 linhas, sem §7–9). A sombra, com os registros das rodadas de rail, é a
  autoridade — como o cabeçalho do `finalize-E.sh` já documenta.
- Os dois testes (`scripts/tests/test-upgrade-lifecycle-hooks-derived.sh`,
  `.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py`) não existem
  no vivo: sem conflito.

Consequência nos materiais rastreados: `EXPECTED_YML_TIMEOUT_MINUTES` 111 → 126
(o V4d do LAND compara o valor EXATO), e a prosa do sentinel, do
`PROPOSED-PATCH.md`, do `README-E.md` e do `COMMIT-MSG-E.txt` acompanha. A
composição do workflow é o único conteúdo novo desde a rodada 5 do rail; a
rodada 6 revisa a sombra re-derivada.

## 11. Rail round 6 — um P1 real na sombra re-derivada, e a cura

**Achado (codex, `gpt-5.6`, sobre a sombra re-derivada do §10):** o merge derivado
lia `settings.base.json` incondicionalmente, mas o `install.sh` constrói o
`settings.json` de um adopter `--ceremony user` a partir de
`templates/settings/settings.user.json` (`WS4-ceremony-settings`) — um perfil que
omite DE PROPÓSITO os 10 hooks de governança que bloqueiam edições ou exigem
GPG/sentinel (`check_plan_edit`, `check_canonical_edit`, `check_tier_policy`,
`check_arbitration_kernel`, …; lista no `_comment` do próprio template). Um upgrade
re-registraria exatamente esses, convertendo em silêncio o perfil advisory em
perfil maintainer — na única população que escolheu não os ter.

**Verificação da claim COMO FEITA (medida, não lida):**

- `settings.base.json` enumera **47** registros; `settings.user.json`, **20**.
  Os nomes só na base são **26** = os **10** excluídos de propósito + **16**
  que a base ganhou depois de 30/07 e nunca chegaram ao template `user`
  (`check_ledger_checkpoint.py` — o próprio achado S328 — entre eles).
- O `upgrade.sh` JÁ resolve a cerimônia num único lugar (`CEREMONY_EFFECTIVE`:
  install-state gravado → `--ceremony` → `CEO_UPGRADE_CEREMONY` → fail-safe
  `user`, §PLAN-166 F3), e todo o resto do upgrader — SPEC/v1, ponteiro
  `PROTOCOL.md`, entrega de `docs/`/`.github/` — consulta essa decisão. O merge
  de hooks era o único consumidor que NÃO consultava.
- **A classe é pré-existente e a wave a alargava.** Os 6 literais pré-cura
  (`check_compact_pinning`, `check_config_change`, `check_postcompact_reinject`,
  `check_precompact_continuity`, `check_setup_verification`,
  `check_subagent_start`) também estão só na base: o upgrader antigo já injetava
  6 registros não-`user` em adopters `user`. Derivar da base inteira levava isso
  de 6 para 27, agora incluindo os 10 bloqueadores. O rail viu o alargamento;
  as rodadas 1–5 não viram (a rodada limpa prova a superfície, não o
  entregável).

**Cura — reutilizar a decisão, não refazê-la.** `_merge_lifecycle_hooks_into_settings`
seleciona o template pelo `CEREMONY_EFFECTIVE`, como o `install.sh` já faz:

```bash
case "${CEREMONY_EFFECTIVE:-}" in
  maintainer) template="$SOURCE_DIR/templates/settings/settings.base.json" ;;
  *)          template="$SOURCE_DIR/templates/settings/settings.user.json" ;;
esac
```

Só o literal `maintainer` seleciona o roster largo; qualquer outro valor —
inclusive a variável NÃO definida, que só um harness produz — toma o template
estreito, a mesma direção fail-SAFE que a própria resolução escolheu em `:884`.
A mensagem de registro passa a NOMEAR o template e a cerimônia
(`derived from templates/settings/settings.user.json — ceremony=user`). O
invariante anti-rot (§V5 / 4g: zero tokens `.py` na função) continua em 0 — a
seleção cita dois `.json`, nenhum hook.

**Testes (todos derivados dos dois artefatos, nunca de uma lista escrita à mão):**

- Unidade, classe nova `TestCeremonySelectsTheTemplate` (8 casos; suíte 49 → 57):
  não-vacuidade (user omite ≥10 da base, e `check_canonical_edit.py` está entre
  eles); `user` reproduz o conjunto de `settings.user.json`; `user` não registra
  NENHUM nome só-na-base; `maintainer` reproduz a base; variável ausente e valor
  desconhecido (`wizard`) caem no template estreito; um install `user` fresco é
  no-op byte a byte; **controle positivo de seleção viva** — um hook plantado só
  no template `user` chega sob `user` e NÃO chega sob `maintainer`. O harness
  passa a carregar os DOIS templates (um scratch source só com a base faria
  todo merge `user` cair no fail-open «template unreadable» e provar nada).
  `TestNoSecondRoster` ganha duas asserções: a função lê o literal
  `settings.user.json` e consome `CEREMONY_EFFECTIVE`.
- **Controle vermelho do oráculo:** a classe nova, rodada contra a função
  PRÉ-cura (o index da sombra antes desta rodada), FALHA; contra a função
  curada, passa. O registro está no log da sessão (`e2e-E-shadow-cure.log`).
- e2e, caso novo **E.14** (9 asserções): install REAL `--ceremony user` (o cache
  do fixture é maintainer e não serve); a cerimônia chega ao upgrade como no
  campo — GRAVADA em `.claude/.install-state.json`, sem flag na chamada;
  E.14a não-vacuidade (≥10 só-na-base); E.14b o registro diz `user`; E.14c o
  install fresco == template `user`; strip de um registro que o template `user`
  DECLARA (para o merge ter trabalho real); E.14d upgrade rc 0; E.14e o
  registro removido volta (merge VIVO, não pulado); **E.14f zero nomes
  só-na-base no adopter `user`**; E.14g conjunto == template `user` de novo;
  E.14h o log nomeia `settings.user.json`; **E.14i controle positivo** — o
  MESMO adopter com o registro reescrito para `maintainer` recebe TODOS os
  só-na-base (a escolha é dirigida pelo registro, e E.14f pode falhar).

**Residual declarado (fora do escopo desta wave — OQ-E5 ao Owner):**
`settings.user.json` está DEFASADO em relação à base: 16 hooks que não são os
excluídos de propósito (advisory, continuidade de compaction, ledger, pair-rail
etc.) existem na base e não no `user`. Esta cura torna o upgrade HONESTO sobre a
cerimônia; ela não pode — e não deve — entregar a um adopter `user` hooks que o
template `user` não declara. A cura da defasagem é OUTRA wave: derivar
`settings.user.json` da base por subtração dos 10 (gerador + teste de paridade),
em vez de mantê-lo como segunda cópia — exatamente a classe que esta wave fecha
no upgrader, uma camada acima. Até lá, um adopter `user` que faça upgrade recebe
os 20 do seu template, e nada mais.

## 12. Rail round 7 — dois P1 e dois P2 sobre a sombra curada, e as curas

Sobre a sombra do §11 (cerimônia seleciona o template; unit 57, e2e 60/0), o
rail devolveu quatro achados. Um é por construção; três são reais e foram
medidos antes de qualquer edição.

**[P1 — por construção, disposto] sentinel sem assinatura.** O
`wave-s329-E-approved.md` traz `TO-FILL-AT-SIGN` e não há `.asc` — porque a
sombra é o estado PRÉ-assinatura por desenho: o `OWNER-S329-E-SIGN.sh` preenche
Anchor/Data/Approved-By e assina; o LAND recusa sem isso (G1). Mesma disposição
das rodadas 2 e 3.

**[P1 — real] o `.env` não viajava com os `.hooks`.** Medido:
`settings.user.json` declara `env.CEO_CONFIG_PROTECTION_ADVISORY=1` e
`check_config_protection.py` (que está nos DOIS templates) só é advisory com
essa chave (`check_config_protection.py` §Escape hatches: «the maintainer
ceremony leaves it unset (BLOCKING)»). O `upgrade.sh` nunca tocava `.env`. Um
adopter `user` anterior ao PLAN-124 — sem o registro E sem a chave — recebia,
pela derivação, o hook na variante BLOQUEANTE, no perfil que escolheu não
bloquear. A base tem 6 chaves de `env` próprias (`CEO_QUIET_MODE`,
`CLAUDE_CODE_SUBAGENT_MODEL`, …), nenhuma delas a advisory.

*Cura — arquitetura, não lista:* o template é o roster dos registros E das
configurações que eles leem. O programa jq passa a derivar também `.env`, com
a MESMA doutrina dos eventos: aditivo chave a chave; um valor que o adopter já
tem NUNCA é sobrescrito; `.env` presente com forma inesperada é PRESERVADO e
NOMEADO (`SKIP-ENV`, resultado PARTIAL); template sem `.env` não inventa a
chave (documento sem `.env` segue byte-idêntico num no-op). O relatório e o
dry-run anunciam `env <chave>` na mesma lista dos hooks; a escrita é o mesmo
`mv` atômico. A alternativa — «pular o registro quando o modo advisory não pode
ser garantido» — exigiria saber QUAL hook depende de QUAL chave: uma segunda
lista, exatamente a classe que esta wave remove.

*Alargamento declarado:* a regra vale para os dois perfis. Um adopter
`maintainer` legado que não tenha as 6 chaves da base passa a recebê-las
(valores dele sempre vencem). É a mesma semântica ADITIVA da wave, uma camada
ao lado; a decisão de recusar chave a chave é a mesma OQ-E1 dos hooks.

**[P2 — real] chave de identidade sem fronteira à esquerda.** Medido em jq
(Oniguruma): `"python3 .claude/hooks/.check_ledger_checkpoint.py"` rendia
`check_ledger_checkpoint.py` com o regex antigo e `[]` com lookbehind. Sem a
fronteira, um comando do adopter que invoque `.check_x.py` ou `-check_x.py`
faz o registro canônico parecer PRESENTE e ele nunca é ligado — e o oráculo
Python dos testes (`_PY_TOKEN`) já tinha o lookbehind: os dois extratores
discordavam. Cura: `(?<![A-Za-z0-9_.-])` no `match` de `_keys`; teste afirma
que os dois extratores carregam a mesma fronteira.

**[P2 — real] template como stream de dois documentos.** Medido: `jq -e` sobre
o arquivo valida os dois documentos (rc 0) e `--slurpfile` carrega 2; o
programa lê `$tpl[0]` e o segundo some em silêncio. Cura: guard fail-closed
antes de qualquer forma — `jq -n --slurpfile t "$template" '$t | length'` tem de
ser exatamente 1; senão NOTE nomeada com o número encontrado e nada é escrito.

**Testes:** unidade +12 (57 → 69): `TestEnvTravelsWithTheRoster` (7: adopter
user legado recebe o `.env` do template inteiro, com a âncora do rail; valor do
adopter nunca sobrescrito — chave derivada; `.env` não-objeto preservado e
nomeado com os hooks ainda mergeados; template sem `.env` não cria a chave;
idempotência byte a byte; dry-run anuncia `env <chave>` e não escreve;
maintainer legado recebe o `.env` da base — o alargamento, afirmado),
`TestTemplateMustBeExactlyOneDocument` (2: stream de 2 recusado e nomeado,
nada escrito; controle — os dois artefatos reais são um documento cada),
`TestHiddenScriptIsNotTheCanonicalRegistration` (3: `.check_x.py`,
`-check_x.py`, paridade das fronteiras). e2e +2 (60 → 62): E.14j — a chave
`user`-only (DERIVADA: chaves de `env` do template `user` menos as da base) é
removida do adopter antes do upgrade e volta com o valor do template; E.14k —
o controle com registro `maintainer` NÃO a recebe (a base não a declara): o
merge de `env` é dirigido pelo template, não por literal.

## 13. Rail round 8 — INFERIDO não é GRAVADO, e a cura

Sobre a sombra do §12 (unit 69, e2e 62/0) o rail devolveu um P1 e um P2, os
dois reais.

**[P1] cerimônia inferida tratada como cerimônia user.** O resolver do
`upgrade.sh` (`:884–:902`) responde `user` sem install-state legível e sem
flag SÓ como fail-safe de ESCRITA NA RAIZ (`_CEREMONY_PERSIST=0`): essa
população é o install histórico pré-Wave-B cuja cerimônia ninguém conhece. A
seleção do §11 lia só o valor e, para um maintainer histórico, (a) retinha
TODOS os hooks só-na-base — `check_ledger_checkpoint.py`, o próprio achado
S328, exatamente para os adopters que esta wave existe para alcançar — e (b)
com o §12, entregava `CEO_CONFIG_PROTECTION_ADVISORY=1`, que transforma em
allow um matcher bloqueante que esse adopter já carrega. Medido: a interseção
dos dois templates é os 20 registros do `user` (todos ⊆ base) e uma única
chave de `env` comum (`CEO_QUIET_MODE=1`); a chave user-only é exatamente a
advisory.

*Cura — uma terceira postura, não um ajuste do default.* A seleção passa a ler
`CEREMONY_EFFECTIVE/_CEREMONY_PERSIST`: `maintainer/1` → base; `user/1`
(gravado, `--ceremony`, `CEO_UPGRADE_CEREMONY`) → user; **qualquer outra
combinação → SHARED**: o roster que os DOIS templates declaram, derivado em
runtime pelo MESMO `_keys` do merge (hooks por chave de identidade; `env` por
chave E valor), escrito em `$BAK_DIR/.claude/settings.template-shared.json`
como artefato de auditoria, e uma NOTE que nomeia a situação, quantifica o que
foi RETIDO por perfil e diz como optar (`--ceremony maintainer|user`). Nada que
um dos perfis recusaria; os 20 em que os perfis concordam chegam. As definições
jq (`_cmds`/`_keys`/`_disp`) foram içadas para `$jq_defs`, compartilhado pelos
dois programas — a fronteira do §12 não pode divergir entre duas cópias.

**[P2] bloco multi-comando parcialmente presente.** Um bloco do template com
vários comandos de que o adopter já tem alguns era appendado INTEIRO
(`all(...)` falha), duplicando os presentes — para sempre, porque o upgrade
seguinte vê a duplicata como presente. Nenhum template shipado tem esse
formato (medido: 0 e 0), mas o guard estrutural o ACEITA. Cura: só as entradas
AUSENTES do bloco são appendadas, cada uma julgada pelas próprias chaves.

**Testes:** unidade (69 → 80): `TestUnknownCeremonyTakesTheSharedRoster` (9:
não-vacuidade; `user/0` recebe o shared e NÃO a chave user-only; unset e valor
desconhecido → shared; o shared ⊆ dos dois templates, `env` inclusive; hook
só-na-base retido + NOTE com opt-in e `WITHHELD:`; artefato de auditoria
escrito e coerente; controles — `user/1` e `maintainer/1` recebem o perfil
inteiro); `TestPartiallyPresentMultiCommandBlock` (2: só a entrada ausente é
appendada, sem duplicar; bloco inteiro presente é no-op byte a byte). Os dois
testes do §11 sobre unset/valor desconhecido passam a afirmar o invariante que
as rodadas 6 e 8 compartilham (nunca o roster largo). e2e +E.15 (7 asserções,
62 → 69): fixture = install maintainer do cache SEM install-state, com um hook
compartilhado, um só-na-base e uma chave de `env` compartilhada removidos —
upgrade sem flag: NOTE (E.15a), compartilhado volta (E.15b), só-na-base
RETIDO (E.15c), `env` compartilhado volta (E.15d), user-only ausente
(E.15e); controles com `--ceremony maintainer` (E.15f) e `--ceremony user`
(E.15g), cada um recebendo o seu perfil inteiro e não o do outro.

## 14. Rail round 9 — a postura SHARED do §13 não era provável; a que é

Sobre a sombra do §13 (unit 80, e2e 69/0) o rail devolveu dois P1 e um P2,
todos sobre a postura SHARED — a segunda cura consecutiva a gerar o achado
seguinte, o sinal de que a ARQUITETURA da cura estava errada, não o remendo.

**[P1] hooks e settings intersectados em separado.** `check_config_protection.py`
está nos DOIS templates (entrava no shared), mas o seu interruptor advisory é
user-only (ficava fora): um adopter `user` legado, sem os dois, recebia o hook
BLOQUEANTE — o §12 de novo, por outra porta. A raiz: a dependência
hook → setting vive no CÓDIGO do hook, que o `upgrade.sh` não lê; nenhuma
interseção de JSON a enxerga.

**[P1] `--dry-run` escrevia.** O branch shared fazia `mkdir -p $BAK_DIR/.claude`
e gravava o roster derivado ANTES do `return` do dry-run — a garantia de
árvore intocada (`:981`) quebrada numa pré-visualização.

**[P2] fontes sem validação.** Os guards de documento único e de forma corriam
só sobre o arquivo derivado; um template-fonte em stream de dois documentos
era coerçido (`$b[0]`) e aplicado truncado onde as posturas explícitas o
recusariam.

**Cura — o que é PROVÁVEL sem roster.** Para cerimônia desconhecida o upgrade
**não registra hook nenhum**. O que os dois perfis provadamente compartilham é
só o conjunto de settings que ambos declaram com o MESMO valor (hoje:
`CEO_QUIET_MODE=1`); isso é aplicado, todo o resto é RETIDO e nomeado
(`WITHHELD: 47 registros + 5 settings da base, 20 + 1 do user`), e o sumário
diz `PARTIAL (ceremony unknown)` — nunca a frase de completude — com o opt-in
`--ceremony maintainer|user`. O pré-cura empurrava 6 literais só-na-base para
essa população; esses 6 eram o defeito. A derivação vai para `mktemp` (trap
`RETURN` apaga); só o caminho que ESCREVE copia o artefato de auditoria para
`$BAK_DIR/.claude/settings.template-shared.json`. As duas fontes passam pelos
mesmos três guards (legível, um documento, objeto com `.hooks` objeto) antes de
qualquer derivação. `$jq_defs` segue içado (um único `_keys`).

**Testes:** unidade (80 → 82): `TestUnknownCeremonyRegistersNoHooks` substitui a
classe do §13 (11 casos: não-vacuidade; `user/0`, unset e valor desconhecido
→ zero hooks + só settings compartilhadas, user-only ausente; NOTE + `PARTIAL`
e nunca «already present»; adopter já atual continua PARTIAL; artefato só no
caminho que escreveu; **dry-run não cria `bak/` nem nada sob `.claude/`**;
fonte em stream de 2 recusada e nomeada ANTES de derivar; controles `user/1` e
`maintainer/1` inteiros). e2e (69 → 71): E.15b INVERTIDO (o hook compartilhado
removido NÃO volta), E.15h (sumário PARTIAL, sem completude), E.15i
(`--dry-run` no adopter desconhecido: sem `.claude.bak`, sem arquivo derivado,
`settings.json` byte-idêntico); E.15f/E.15g seguem provando que, com a
cerimônia DITA, cada perfil chega inteiro.

## 15. Rail round 10 — um P2 sobre a forma do template, e a cura

Sobre a sombra do §14 (unit 82, e2e 71/0) o rail devolveu um único P2, sem
bloco `Full review comments:` — tratado como achado mesmo assim: um template
cujo `.env` está PRESENTE mas não é objeto era coerçido a `{}` na derivação e
os seus hooks entravam sem as settings que os mantêm no modo do perfil (para
`settings.user.json`, `check_config_protection.py` sem a advisory). Nenhum
template shipado tem essa forma; o guard a aceitava.

**Cura:** o guard estrutural do template (o mesmo que recusa evento não-array
e bloco não-identificável) emite `ENV (<tipo>)` quando `.env` está presente e
não é objeto — recusa integral, nomeada, nada escrito. Um template SEM `.env`
continua válido (não inventa chave); um `.env` vazio (`{}`) também.

**Testes:** unidade 82 → 84 (`TestTemplateEnvMustBeAnObject`: template com
`env: [1]` recusado e nomeado com `settings.json` intocado; controle com
`env: {}` merge normal e sem chave inventada). O e2e não muda (71).

## 16. Rail round 11 — três P2 na periferia, e as curas

Sobre a sombra do §15 (unit 84, e2e 71/0) o rail devolveu o P1 do sentinel
(por construção, pré-SIGN) e três P2 reais, todos na periferia do que os
rounds 8–10 introduziram:

- **scratch dentro do alvo.** O `mktemp` da postura SHARED usava
  `${TMPDIR:-/tmp}` cru; com `TMPDIR` apontando para dentro do `$TARGET` o
  arquivo derivado nasceria no adopter — inclusive num `--dry-run`. O
  `upgrade.sh` já tem `_up_tmpbase()` (cai para `/tmp` quando `TMPDIR` está
  sob o alvo) e todos os outros scratch files passam por ele. Cura: este
  também.
- **trap com path interpolado.** `trap "rm -f '$path'" RETURN` faz o bash
  re-parsear o path quando o trap dispara: um apóstrofo inocente aborta sob
  `set -e`, um path forjado injeta. Cura: corpo do trap FIXO em aspas simples
  (`trap 'rm -f -- "$_UP_SHARED_TPL_TMP"' RETURN`) com a variável — global,
  não `local` — expandida só na execução. Medido antes de escrever: o trap
  `RETURN` enxerga a global e remove o arquivo.
- **`settings.json` que não é UM documento.** Vazio ou stream de vários
  objetos: o `jq` aceita streams, então o vazio produzia relatório vazio e a
  frase de completude (falsa), e o stream produzia várias saídas que o
  validador de objeto aceitava — o `mv` instalaria um arquivo que consumidores
  JSON comuns não leem. Cura: o mesmo guard de documento único que o template
  já tem, agora sobre o `settings.json` do adopter, antes do report —
  vazio/stream ⇒ NOTE nomeada com a contagem, PRESERVADO; JSON inválido segue
  na mensagem antiga («malformed settings.json»).

**Testes:** unidade 84 → 88 — `TestSettingsMustBeExactlyOneDocument` (2:
vazio e stream de 2 recusados e nomeados, arquivo intocado, sem frase de
completude) e `TestScratchStaysOutsideTheTarget` (2: com `TMPDIR` dentro do
`$TARGET`, um `--dry-run` de cerimônia desconhecida — que deriva o roster — não
deixa NADA no adopter, usando o `_up_tmpbase` REAL extraído do `upgrade.sh`;
e o invariante textual — a função chama `_up_tmpbase` e o trap não interpola).
O e2e não muda (71).
