# Rail round 1 — curas dos 4 achados sobre `check-stale-module-patch.py`

**PLAN-179 · night-run S329 · U2 (instrumento)**
Rail auditado: `338eac5`. Árvore viva no momento da cura: `1d293dc` (a fase 2 de
curas já havia landado; ver §5 — a linha de base do DELTA é a árvore VIVA, não o
relatório do censo).
Entregáveis: `.claude/scripts/check-stale-module-patch.py`,
`.claude/scripts/tests/test_check_stale_module_patch.py`. Nenhum commit.

---

## 1. Achado → cura → prova

### [P1] Achado 1 — o rebind de `setUp` era creditado ao ARQUIVO inteiro

`:495-498` rebaixava para `LOOKUP-VIVO` qualquer sítio de um arquivo que
tivesse *algum* `setUp` com rebind vivo. `live_rebinds` guardava só
`(função, linha)` — sem classe e sem alias.

**Cura** (`check-stale-module-patch.py`):

| O quê | Onde |
|---|---|
| pilha de classes no scanner (`visit_ClassDef`) | `:351-355` |
| `live_rebinds` vira registro com `class` / `func` / `alias` / `line` | `:526-533` |
| sítios carregam `class` e `alias_head` | `:548-564` |
| casamento por CLASSE **e** por ALIAS antes de rebaixar | `:685-703` |
| exigência de `global` (sem ela a atribuição liga um LOCAL) | `:103-122`, `:523-525` |
| forma nova `local-rebind` ⇒ `INDETERMINADO`, nunca descartada | `:100`, `:705-712` |

Duas escolhas conservadoras, ambas erram para FRAGIL e estão no docstring
(`:37-49`): um `setUp` **herdado** (`class B(A)`) não é creditado a `B`, e um
rebind sem `global` não rebaixa nada.

**Prova — reprodução na ÁRVORE VIVA** (poluidor sintético do §4 do censo:
`sys.modules.pop` + `delattr(_lib,"audit_emit")` + import fresco, abortando se
`old is new`):

```
PYTHONPATH=<tmp>/pollute python3 -m pytest \
  .claude/hooks/tests/test_spool_drain_rotation_race.py -q -p no:cacheprovider \
  -p polluter_plugin -k SpoolDrainPathRotationRace
```

| Execução | Resultado |
|---|---|
| classe 2 sozinha, SEM poluidor | 1 passed |
| **classe 2 sozinha, COM poluidor** | **1 failed** — `ImportError: module _lib.audit_emit not in sys.modules` (o `setUp` dela, `:259`) |
| arquivo inteiro, COM poluidor | 4 passed (o `setUp` da classe 1 roda antes) |
| classe 1 sozinha, COM poluidor | 3 passed (ela é dona do rebind) |

O censo dizia `LOOKUP-VIVO` para um sítio que levanta `ImportError` quando a
classe roda sozinha — que é exatamente o que acontece sob `-n auto`. Falso-safe
confirmado, não teórico.

---

### [P2] Achado 2 — `SEGURO` concedido por SUBSTRING no nome do atributo

`:409-413` classificava como alias-do-consumidor qualquer expressão de atributo
terminada em `audit_emit`, sem provar (a) que a base é o módulo sob teste nem
(b) que o atributo é de fato um alias de `_lib.audit_emit`.

**Cura**: `_verdict_for_consumer_site()` (`:594-672`), alimentado por um mapa
`nome local → stem de módulo` construído dos `import` do arquivo de teste
(`_bind_module_alias`, `:356-366`; resolução no driver, `:888-893`, depois de o
arquivo inteiro ter sido visitado). As duas sub-formas passam a ser distinguidas
no scanner (`:475-497`):

| Situação | Veredito | Critério impresso |
|---|---|---|
| base não vem de `import` (loader dinâmico, variável local, rebind ambíguo) | `INDETERMINADO` | nomeia a base |
| base vem de `import` mas o módulo está FORA das raízes indexadas | `INDETERMINADO` | nomeia o módulo e a raiz |
| `X._alias` patcheado como OBJETO e `_alias` não é alias PROVADO de `_lib.audit_emit` em `X` | `INDETERMINADO` | lista os aliases provados |
| `patch.object(X, "_alias")` e `_alias` **não** é alias de `_lib.audit_emit` | `SEGURO` | "o NOME apenas contém `audit_emit`; `patch.object` troca o atributo NO LUGAR" |
| alias provado **e** consumidor `import-time-module` | `SEGURO` | teste e consumidor leem a MESMA referência |
| alias provado mas consumidor `call-time` (misto) | `INDETERMINADO` | "ao menos um caminho re-resolve o emissor" |

O caso real que isso destrava: `check_agent_spawn.py:73` liga
`from _lib import audit_emit_dispatch as _audit_emit` — o `_audit_emit` de 23
sítios **não é** um alias de `_lib.audit_emit`. O veredito continua `SEGURO`,
mas agora por um motivo verdadeiro e impresso, em vez de por casamento de nome.

**Prova**: 6 testes novos (`:765`, `:787`, `:814`, `:836`, `:865`, `:893`) +
mutante M2 (§4).

---

### [P2] Achado 3 — o "controle positivo" nunca executava o perigo

`test_check_stale_module_patch.py:282-290` só escrevia strings e perguntava ao
classificador o veredito DELE. Nenhum import, nenhuma execução do consumidor,
nenhum `sys.modules.pop`.

**Cura**: bloco de controle de RUNTIME no mesmo processo (`:937-1213`):

- pacote-sombra `shadowpkg_<uuid>/_lib/` em `tmp_path`, com nome único — não
  pode tocar o `_lib` do repo, e ainda assim casa a regra de importação do
  instrumento (`base.endswith("._lib")`), de modo que **os mesmos bytes**
  alimentam as duas pernas (identidade de conteúdo asserida, `:1148-1155`);
- `_pollute()` (`:1080-1090`) executa a sequência real — `sys.modules.pop`,
  `delattr` no atributo do pacote, import fresco — e **aborta** se
  `new is old` (controle inerte impossível);
- `_import_sandbox()` (`:1061-1077`) remove todo traço do pacote de
  `sys.modules`/`sys.path` no `finally`.

Duas pernas que EXECUTAM:

| Teste | O que roda | Asserção |
|---|---|---|
| `test_runtime_hazard_is_real_and_the_classifier_agrees` (`:1104`) | importa os 2 módulos de teste, polui, chama `test_emits()` | RED: o patch no alias stale **não** intercepta (`AssertionError`) e o emissor REAL registra 1 chamada no módulo FRESCO. GREEN: a forma de lookup vivo intercepta (`CALLS == []`). Depois exige `FRAGIL` / `LOOKUP-VIVO` do classificador sobre os MESMOS bytes |
| `test_runtime_setup_rebind_is_order_dependent_and_class_scoped` (`:1164`) | duas classes, só a primeira rebinda | `ClassB.setUp()` sozinha levanta `ImportError ... not in sys.modules`; depois de `ClassA.setUp()` ela passa. Exige `FRAGIL` para os sítios de `ClassB` |

O segundo é o teste que o rail pediu: com o achado 1 revertido, ele fica
VERMELHO (§4, mutante M1) — o modelo do classificador é confrontado com a
realidade, não com um rótulo esperado.

---

### [P2] Achado 4 — censo sem raiz de teste retornava sucesso vazio

**Cura**: `census_test_dirs()` extraído (`:829-834`); `main()` valida ≥1 raiz
existente ANTES de varrer e sai `2` com a lista do que procurou
(`:1032-1039`); `run_census` passa a publicar `test_dirs_present`, e o
cabeçalho de INPUTS marca cada raiz ausente com `(ABSENT)`.

**Prova**: `test_hooks_without_any_test_dir_is_usage_error` (`:917`, rc=2 +
mensagem) e a perna negativa `test_one_present_test_dir_is_enough` (`:925`).

---

## 2. DELTA DE VEREDITOS na árvore viva

Antes/depois medidos com o MESMO comando sobre a MESMA árvore (`1d293dc`):
`python3 .claude/scripts/check-stale-module-patch.py --json`.

| | antes | depois |
|---|---:|---:|
| sítios | 105 | **105** (nenhum descartado, nenhum inventado) |
| `FRAGIL` | 0 | **3** |
| `INDETERMINADO` | 19 | **30** |
| `SEGURO` | 40 | **29** |
| `LOOKUP-VIVO` | 46 | **43** |

**14 sítios mudaram de veredito. Nenhum outro.**

### 2.1 Falso-safe REPRODUZIDO — cura devida (achado 1)

| Path | Linha | Forma | antes → depois | Classe dona |
|---|---:|---|---|---|
| `.claude/hooks/tests/test_spool_drain_rotation_race.py` | 259 (`setUp`) | `reload-stale` | `LOOKUP-VIVO` → **`FRAGIL`** | `SpoolDrainPathRotationRaceTest` |
| `.claude/hooks/tests/test_spool_drain_rotation_race.py` | 299 | `reload-stale` | `LOOKUP-VIVO` → **`FRAGIL`** | idem |
| `.claude/hooks/tests/test_spool_drain_rotation_race.py` | 324 | `reload-stale` | `LOOKUP-VIVO` → **`FRAGIL`** | idem |

Cura recomendada: **C3** do censo (§6) — `global audit_emit; audit_emit =
importlib.reload(importlib.import_module("_lib.audit_emit"))` no `setUp:243` da
SEGUNDA classe. Um sítio cura os três. Precedente na própria classe 1 do mesmo
arquivo (`:66-68`). Oráculo de canonicidade do arquivo: `0` (livre, commit
direto).

> Os outros dois arquivos com rebind vivo (`test_audit_emit_rotation.py`,
> `test_audit_emit_chain_length.py`) foram medidos e estão LIMPOS: todos os
> sítios pertencem à classe que é dona do rebind.

### 2.2 `SEGURO` sem prova → `INDETERMINADO` (achado 2)

Nenhum destes tem vermelho reproduzido; são sítios cuja segurança o instrumento
**não consegue provar**. Duas causas distintas, com remediações distintas:

**(a) base não vem de `import` — módulo carregado dinamicamente (9 sítios)**

| Path | Linhas | Base |
|---|---|---|
| `.claude/hooks/tests/test_anti_ceo_overhead.py` | 493, 528 | `hook` |
| `.claude/hooks/tests/test_bash_citation_gate.py` | 551, 557 | `cbs` |
| `.claude/hooks/tests/test_check_ledger_checkpoint.py` | 136, 1043 | `HOOK` |
| `.claude/hooks/tests/test_fact_gate_deny_once.py` | 580, 635, 657 | `cbs` |

Todos vêm de `X = _load_...()` sobre `importlib.util.spec_from_file_location`.
O consumidor real (`check_bash_safety`, `check_ledger_checkpoint`) **é**
`import-time-module` com alias `_audit_emit` — provavelmente seguros — mas isso
só é confirmável por leitura humana ou trocando o loader por um `import`. Não
inventei uma regra de loader: fechar essa classe por padrão textual é o
anti-padrão 6 do PLAN-185.

**(b) consumidor FORA das raízes indexadas (2 sítios)**

| Path | Linhas | Módulo |
|---|---|---|
| `.claude/hooks/tests/test_mcp_canonical_guard.py` | 550, 555 | `_lib/mcp/canonical_guard.py` |

`build_target_index` varre só `.claude/hooks/*.py` e `.claude/hooks/_lib/*.py`
— o subpacote `_lib/mcp/` nunca foi classificado. É lacuna de ESCOPO do
instrumento (OQ nova, §6), não defeito do teste.

### 2.3 O que NÃO mudou e por quê

Os 23 sítios `patch.object(<check_agent_spawn>, "_audit_emit")` em 4 arquivos
(`test_wiredeadmod_spawn_wiring.py` ×11, `..._model_routing_mode.py` ×7,
`..._file_assignment.py` ×3, `..._routing_promotion.py` ×2) seguem `SEGURO`, mas
o critério mudou de "patch cai num atributo do módulo sob teste" para o motivo
real: `_audit_emit` ali é alias de `_lib.audit_emit_dispatch`, e
`patch.object` troca o atributo NO LUGAR — nenhuma resolução de
`_lib.audit_emit` participa. Os 2 sítios de
`_lib/tests/test_memory_shared_fence.py` seguem `SEGURO` agora com prova
afirmativa (`ms` → `memory_shared`, `import-time-module`, alias `_audit_emit`).

### 2.4 Nota sobre a linha de base

O relatório do censo (`...-S329.md`) foi escrito sobre `b07be9b`. A fase 2 de
curas landou em `1d293dc` e mexeu na árvore: `FRAGIL` 17 → 0, `reload-stale`
12 → 10, `direct-assign` 10 → 4, `obj-alias` 8 → 3, `live-rebind` 1 → 3. Por
isso o DELTA acima é **árvore viva antes da cura do rail × árvore viva depois**,
que é a comparação que isola o efeito destas quatro curas.

---

## 3. Verificações pedidas

| Comando | Resultado |
|---|---|
| `python3 -m pytest .claude/scripts/tests/test_check_stale_module_patch.py -q -p no:cacheprovider` | **39 passed** (26 antes + 13 novos) |
| `python3 .claude/scripts/check-test-env-hygiene.py` | **rc=0** — "0 flagged files" |
| `python3 .claude/scripts/check-stale-module-patch.py --strict` (árvore viva) | **rc=1** (30 `INDETERMINADO`; era rc=1 com 19 — o regime não mudou) |
| `python3 .claude/scripts/check-stale-module-patch.py --json` | rc=0, 105 sítios |

**Higiene da cadeia VIVA.** Snapshot do log antes, corrida da suíte, diff das
linhas acrescentadas: **1 linha**, `action=tool_call_lifecycle_recorded`,
`session_id=bc917148-eaee` — o hook da própria sessão para a chamada Bash que
envolveu o pytest. Zero `policy_*` / `ledger_*`, zero `session_id` vazio. Os
testes novos, incluindo o controle de runtime, **não escrevem na cadeia**.

---

## 4. Prova de que o verde vale (mutantes plantados)

Cada mutante aplicado sobre a árvore curada, suíte rodada, árvore restaurada e
conferida com `cmp` (byte-idêntica em todos os casos).

| # | Mutante | Efeito |
|---|---|---|
| M1 | escopo de classe/alias do achado 1 removido (volta ao rebaixamento por arquivo) | **3 failed** — `..._does_not_travel_to_another_class`, `..._is_scoped_to_the_alias_it_rebinds` e **`test_runtime_setup_rebind_is_order_dependent_and_class_scoped`** |
| M2 | `obj-consumer` volta a `SEGURO` incondicional | **4 failed** / 34 passed |
| M3 | validação de raiz do censo desligada | **1 failed** / 37 passed |
| M4 | poluidor tornado INERTE (`new = old`) | **2 failed** — as duas pernas de runtime abortam com "polluter INERT" |
| M5 | cura falsificada (`_live_audit_emit()` devolve o global stale) | **1 failed** — a perna GREEN acusa |

M1 é a resposta direta ao achado 3: com o modelo do classificador errado, o
controle de runtime fica vermelho. M4 e M5 provam que as duas pernas do controle
executam o mecanismo — não são decorativas.

---

## 5. O que NÃO foi feito

- **Nenhum commit, nenhum `git add`.** Dois arquivos modificados, nada mais.
- **Nenhuma cura nos 14 sítios do DELTA.** São despacho do CEO (§2.1 tem
  vermelho reproduzido e cura com precedente; §2.2 é confirmação de leitura).
- **`build_target_index` não foi ampliado** para `_lib/mcp/` — mudaria o escopo
  do censo no meio de uma rodada de rail.
- **Nenhuma regra para reconhecer loaders dinâmicos.** A classe "resolver mais
  uma forma" é exatamente a que o PLAN-185 mandou parar de perseguir.

---

## 6. Questões abertas novas

- **OQ-6 — escopo do índice de alvos.** `_lib/mcp/` (e qualquer subpacote de
  `_lib/`) nunca é classificado, então todo sítio cujo consumidor viva lá sai
  `INDETERMINADO` por construção. Ampliar o glob é 1 linha, mas muda a
  população do censo: decisão de escopo, não de implementação.
- **OQ-7 — `setUp` herdado.** Hoje um `setUp` com rebind vivo numa classe-base
  não é creditado às subclasses (erra para FRAGIL). Nenhum caso na árvore viva
  hoje; se aparecer, será falso alarme visível, não falso-safe.
- **OQ-8 — os 9 sítios de loader dinâmico (§2.2a).** A remediação barata é
  trocar `X = _load_...()` por um `import` real nos testes, o que torna a prova
  mecânica. É mudança nos testes de hooks, não no instrumento.
- **OQ-5 do censo continua aberta e agora pesa mais:** `--strict` sai rc=1 com
  30 `INDETERMINADO`. Se o instrumento for ao CI, precisa de baseline congelado
  ou de modo advisory.
