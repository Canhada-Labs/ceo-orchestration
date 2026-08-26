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
RESULT: 29 passed, 0 failed
# ~5 min 40 s: 7 invocações de upgrade (6 reais + 1 --dry-run) e 6 adopters
# (1 install real de ~18 s, 5 cópias do cache).
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
23 passed in 0.83s
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

**OQ-E4 — ⛔ O TESTE e2e NASCE DESLIGADO, e isso é bloqueante.**
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
