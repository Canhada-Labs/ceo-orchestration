# Censo mecânico — classe "patch em objeto stale de `_lib.audit_emit`"

**PLAN-179 · night-run S329 · U2 fase 1 (instrumento + censo + reproduções; SEM curas)**
Base: `main` @ `b07be9b`. Tudo derivado por AST e por REPRODUÇÃO; nenhum número
deste documento vem de `grep`.

---

## 1. A classe, e o que ela realmente exige

O LAND do pacote D (S328) abortou com 4 falhas em
`test_ledger_provenance.py::TestDiscardIsVisible` — flake de ORDEM sob
`pytest -n auto`. Mecanismo: o teste patchava o `audit_emit` importado no TOPO
do arquivo enquanto `_lib/ledger_provenance.py::_emit_rejection` resolve
`from _lib import audit_emit` NA CHAMADA. Um predecessor no mesmo worker
(`test_check_agent_spawn.py::TestPLAN078Wave1ModelRoutingAdvisory` re-cria o
módulo no `tearDown`) deixa o nome do arquivo de teste STALE; o patch cai num
objeto que ninguém lê. Curado em `41fe0c9`.

**A assimetria que define a classe.** Quando o CONSUMIDOR também liga em
tempo de import, consumidor e teste ficam stale JUNTOS, no mesmo objeto, e o
patch continua valendo. Só um consumidor que re-resolve na CHAMADA busca um
objeto novo enquanto o teste segura o velho. Por isso o veredito depende de
DUAS coisas — a forma do patch **e** a forma de resolução do alvo — e nenhuma
das duas é observável por texto.

---

## 2. Instrumento

`/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-stale-module-patch.py`
(advisory, stdlib, ≥3.9; NÃO é membro do manifesto ADR-192).

Comando do censo:

```
python3 .claude/scripts/check-stale-module-patch.py            # texto
python3 .claude/scripts/check-stale-module-patch.py --json     # dados
python3 .claude/scripts/check-stale-module-patch.py --strict   # rc=1 se houver INDETERMINADO
```

Exit codes: `0` censo ok · `1` `--strict` com ≥1 INDETERMINADO · `2` erro de
uso / raiz não encontrada · `3` falha de parse que encolheria o censo em
silêncio.

**Regra INVERTIDA (anti-padrão 6 do PLAN-185).** O instrumento enumera as
formas que consegue PROVAR seguras; todo o resto é `INDETERMINADO`. `SEGURO`
é afirmação com critério impresso, nunca default. Um `patch`/`setattr`/
`reload` cuja forma não casa com nenhuma regra vira `unmodelled-form`
(=`INDETERMINADO`) — **nunca é descartado**.

### Inputs medidos (o instrumento os imprime)

| Input | Valor |
|---|---|
| Arquivos de teste varridos | **353** (`.claude/hooks/tests` 327 + `.claude/hooks/_lib/tests` 26, recursivo) |
| Módulos-alvo indexados | **130** (`.claude/hooks/*.py` + `.claude/hooks/_lib/*.py`) |
| Falhas de parse | **0** |

### Lado do CONSUMIDOR (como o alvo resolve o emissor)

| Resolução | N | Significado |
|---|---|---|
| `call-time` | **38** | `from _lib import audit_emit` / `import_module` / `sys.modules[...]` DENTRO da função ⇒ **faz o patch de topo ficar frágil** |
| `import-time-module` | **15** | ligação no nível do módulo ⇒ staleness compartilhada ⇒ patch de topo continua valendo |
| `import-time-function` | 0 | — |
| `indeterminado` | 0 | — |

### Sítios por forma e veredito

**105 sítios em 29 arquivos.**

| Forma | N | | Veredito | N |
|---|---:|---|---|---:|
| `obj-consumer` | 36 | | `SEGURO` | **40** |
| `obj-live-lookup` | 22 | | `LOOKUP-VIVO` | **29** |
| `string-target` | 16 | | `INDETERMINADO` | **19** |
| `reload-stale` | 12 | | `FRAGIL` | **17** |
| `direct-assign` | 10 | | | |
| `obj-alias` | 8 | | | |
| `live-rebind` | 1 | | | |

### O que o instrumento aprendeu DURANTE o censo (3 correções pagas)

1. **`importlib.reload(<alias de módulo>)` é sítio da mesma classe** e não
   estava modelado. `reload()` exige `sys.modules[name] is module`; um objeto
   stale levanta `ImportError` na hora. Descoberto pela REPRODUÇÃO, não pela
   leitura: `test_audit_emit_chain_length.py` falhou com o poluidor no
   `setUp:78`, e o sítio que o censo tinha marcado (`:117`) não era o culpado.
   A forma trouxe **12 sítios em 3 arquivos**, dois deles nunca contados
   (`test_audit_emit_rotation.py`, `test_spool_drain_rotation_race.py`).
2. **Falso-positivo por rebind vivo.** `test_spool_drain_rotation_race.py:67-68`
   já carrega uma CURA que ninguém havia catalogado —
   `audit_emit = importlib.reload(importlib.import_module("_lib.audit_emit"))`
   no `setUp` — e por isso os 6 `reload` daquele arquivo NÃO quebram. O censo
   os marcava FRAGIL. Corrigido: rebind vivo em `setUp` rebaixa para
   `LOOKUP-VIVO`, com a ressalva de ordem impressa no critério.
3. **Drop silencioso.** `patch.object(<módulo>._audit_emit, "emit_x")` (o
   alias do próprio consumidor como arg0) não casava com nenhuma regra e
   sumia — 8 sítios em 3 arquivos, incluindo os 2 únicos de
   `_lib/tests/`. Fechado, e um teste de cruzamento independente
   (`test_no_patch_shaped_emitter_mention_escapes_the_census`) agora varre a
   árvore real e reprova se qualquer chamada patch-shaped que nomeie o
   emissor ficar de fora.

> **A claim do rail-round-7 está REFUTADA.** Ele afirmava "~22 arquivos com
> `patch.object(audit_emit…)` + ~5 string-target". Medido: **8** sítios
> `obj-alias` em 6 arquivos e **16** string-target em 3 arquivos. O grep
> superestimava a família `patch.object` e era **cego** às famílias
> `reload-stale` (12) e `direct-assign` (10), que é onde estava metade do
> risco real.

---

## 3. Testes do instrumento

`/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/tests/test_check_stale_module_patch.py`
— **26 passed**.

```
python3 -m pytest .claude/scripts/tests/test_check_stale_module_patch.py -q -p no:cacheprovider
```

Árvores-sombra em `tmp_path`, script dirigido por `--root`; zero mutação de
`os.environ`, `$HOME` e `$CLAUDE_PROJECT_DIR` nunca tocados.
`check-test-env-hygiene.py --paths <arquivo>` ⇒ **rc=0**, "0 flagged files".

**Controle positivo mais forte:** `test_s329_incident_shape_precure_is_fragil`
/ `..._postcure_is_lookup_vivo` replicam as formas pré e pós-cura de
`test_ledger_provenance.py` e exigem que o veredito VIRE entre elas.

**Prova de que o verde vale (mutantes plantados, todos mortos, árvore
restaurada byte-idêntica por `cmp`):**

| Mutante | Efeito |
|---|---|
| detecção `call-time` de `ImportFrom` desligada | **4 failed** / 19 passed |
| detecção de `reload` desligada | **4 failed** / 19 passed |
| detecção de rebind vivo desligada | **1 failed** / 22 passed |
| rebind aceito em qualquer função (não só `setUp`) | **1 failed** / 22 passed |

---

## 4. Reproduções determinísticas (poluidor sintético, mesmo processo)

Poluidor: plugin pytest em `pytest_collection_finish` (depois do import dos
módulos de teste, antes de qualquer teste) que faz exatamente o que o poluidor
real faz — `sys.modules.pop("_lib.audit_emit")`, `delattr(_lib,"audit_emit")`,
`importlib.import_module` fresco. **O plugin ABORTA se o objeto novo for o
mesmo que o velho**, então um controle inerte é impossível: as 6+2 execuções
imprimiram `POLLUTER: rebound _lib.audit_emit old_is_new=False`.

```
# BASE
PYTHONPATH=<tmp>/pollute python3 -m pytest <arquivo> -q -p no:cacheprovider
# POLUÍDO
PYTHONPATH=<tmp>/pollute python3 -m pytest <arquivo> -q -p no:cacheprovider -p polluter_plugin
```

| Arquivo | BASE | POLUÍDO | Leitura |
|---|---|---|---|
| `test_advisory_dampen.py` | 25 passed | **2 failed** / 23 passed | **FRAGIL confirmado** — `:289`, `:304` |
| `test_audit_emit_chain_length.py` | 11 passed | **11 failed** | **FRAGIL confirmado** — `setUp:78` |
| `test_audit_emit_rotation.py` | 9 passed | **5 failed** / 4 passed | **FRAGIL confirmado** |
| `test_spool_drain_rotation_race.py` | 4 passed | 4 passed | rebind vivo no `setUp` ⇒ rebaixado a `LOOKUP-VIVO` |
| `test_check_arbitration_kernel_v214.py` | 7 passed | 7 passed | **VACUOSO** (ver §5) |
| `test_tool_lifecycle.py` | 27 passed | 27 passed | **VACUOSO** |
| `test_tool_lifecycle_observe.py` | 26 passed | 26 passed | xfail-advisory (ver §5) |
| `test_tool_lifecycle_perf.py` | 1 xfailed | 1 xfailed | xfail-advisory |

Execuções isoladas por teste (mesmo par BASE/POLUÍDO):

| Teste | BASE | POLUÍDO |
|---|---|---|
| `test_audit_emit_chain_length.py::CanaryWiringTests::test_canary_skip_when_HMAC_unavailable` | 1 passed | **1 failed** (`ImportError: module _lib.audit_emit not in sys.modules`, em `setUp:78`) |
| `test_advisory_dampen.py::TestCondensationAuditEvent::test_emit_failure_is_fail_open_full_behavior` | 1 passed | 1 passed |
| `test_check_arbitration_kernel_v214.py::TestAuditBlockNeverRaises::test_does_not_raise_on_audit_emit_emit_failing` | 1 passed | 1 passed |
| `test_tool_lifecycle.py::TestFailOpen::test_record_post_swallows_emit_exception` | 1 passed | 1 passed |

A falha reproduzida em `test_advisory_dampen` é `assertEqual(len(dampened), 1)`
— o recorder não viu nada, que é a assinatura exata da classe.

**Higiene da cadeia VIVA.** Snapshot antes = 14.068 linhas. Durante o trabalho
o log ROTACIONOU normalmente (manifesto `2026-08-26T19:37:46Z`, arquivo
`audit-log-2026-08-2.jsonl` com 14.267 linhas); conservação bate. No segmento
corrente: **0 linhas com ação de assinatura de suíte** (`policy_*`, `ledger_*`,
`advisory_dampened`). As linhas com `session_id` vazio são o
`chain_reset_marker` da rotação e eventos de hook da própria sessão. **As
reproduções não contaminaram a cadeia.**

---

## 5. Três subclasses distintas — só uma é flake

O poluidor separou o que o AST sozinho não separa.

**(a) FLAKE DE ORDEM — vermelho reproduzido. 10 sítios / 3 arquivos.**
O patch não chega, a asserção depende dele, o teste cai. É a classe que
abortou o land de D.

**(b) VACUOSO SOB STALENESS — 5 sítios / 3 arquivos.** O sítio tem a forma
frágil, mas a asserção não distingue patch-aplicado de patch-perdido. Padrão:
patcha com `side_effect=RuntimeError(...)` e afirma apenas que a chamada NÃO
levanta. Se o patch fica stale, o emissor REAL roda, também não levanta, e o
teste passa. Não é flake — é pior de um jeito diferente: *o teste não pode
ficar vermelho*, então nunca provou o fail-open que diz provar.
Sítios: `test_advisory_dampen.py:317`, `test_check_arbitration_kernel_v214.py:147`,
`test_tool_lifecycle.py:442,450`.

**(c) CONTAMINAÇÃO DE MEDIÇÃO — 4 sítios / 2 arquivos.** Em
`test_tool_lifecycle_observe.py:750,775` e `test_tool_lifecycle_perf.py:69,91`
a atribuição direta instala um `lambda` no-op só para tirar o custo do emissor
do cronômetro. Se ficar stale, o emissor REAL entra na janela medida e o p99
passa a medir outra coisa. Os dois testes são `@pytest.mark.xfail(strict=False)`
advisory, então **não têm como acusar** — o orçamento de perf silenciosamente
mede o alvo errado.

---

## 6. Lista de cura para a fase 2

Formas de cura, todas com precedente NA ÁRVORE:

- **C1 — lookup vivo** (`test_ledger_provenance.py:80`): helper
  `_live_audit_emit()` que faz `from _lib import audit_emit as _ae; return _ae`
  e patcha o objeto retornado. Para `obj-alias`.
- **C2 — atribuição sobre objeto vivo**: `_ae = _live_audit_emit()` e então
  `_ae.emit_x = fake` / restauração no mesmo `_ae`. Para `direct-assign`.
- **C3 — rebind do global no `setUp`** (`test_spool_drain_rotation_race.py:67-68`):
  `audit_emit = importlib.reload(importlib.import_module("_lib.audit_emit"))`.
  Para `reload-stale`; cura o arquivo inteiro num sítio só.

### CURE_LIST_FREE — `.claude/hooks/tests/` (commit direto)

| # | Path | Linhas | Forma | Cura | Canon. | Prioridade |
|---|---|---|---|---|:---:|---|
| 1 | `.claude/hooks/tests/test_audit_emit_rotation.py` | 37 (`setUp`), 80, 118, 147 | `reload-stale` | **C3** no `setUp:37` | 0 | **P1 — vermelho reproduzido** |
| 2 | `.claude/hooks/tests/test_audit_emit_chain_length.py` | 78 (`setUp`), 129 | `reload-stale` | **C3** no `setUp:78` | 0 | **P1 — vermelho reproduzido** |
| 3 | `.claude/hooks/tests/test_advisory_dampen.py` | 289, 304 | `obj-alias` | **C1** | 0 | **P1 — vermelho reproduzido** |
| 4 | `.claude/hooks/tests/test_audit_emit_chain_length.py` | 117 | `obj-alias` | **C1** | 0 | P2 — coberto por (2), mas a forma fica |
| 5 | `.claude/hooks/tests/test_advisory_dampen.py` | 317 | `obj-alias` | **C1** + tornar a asserção dependente do patch | 0 | P2 — vacuoso |
| 6 | `.claude/hooks/tests/test_check_arbitration_kernel_v214.py` | 147 | `obj-alias` | **C1** + idem | 0 | P2 — vacuoso |
| 7 | `.claude/hooks/tests/test_tool_lifecycle.py` | 442, 450 | `direct-assign` | **C2** + idem | 0 | P2 — vacuoso |
| 8 | `.claude/hooks/tests/test_tool_lifecycle_observe.py` | 750, 775 | `direct-assign` | **C2** | 0 | P3 — contamina medição |
| 9 | `.claude/hooks/tests/test_tool_lifecycle_perf.py` | 69, 91 | `direct-assign` | **C2** | 0 | P3 — contamina medição |

Itens 1–3 são os que ficam vermelhos hoje sob ordem adversa; 4–9 são forma
frágil sem vermelho reproduzível — curar por higiene, não por incêndio.
**Canon. = dígito medido do oráculo** (§6.1): os 9 respondem `0` = livres,
então a lista inteira é commit direto, sem cerimônia.

### CURE_LIST_GUARDED — `.claude/hooks/_lib/tests/` (pacote)

**Vazia — agora por MEDIÇÃO, não por precaução.**

| Path | Linhas | Forma | Veredito | Canon. |
|---|---|---|---|:---:|
| `.claude/hooks/_lib/tests/test_memory_shared_fence.py` | 140, 152 | `obj-consumer` | `SEGURO` | **1** |

O único arquivo de `_lib/tests/` com sítios **é** guarded (dígito `1`), então
qualquer cura nele exigiria cerimônia — mas os dois sítios são `SEGURO` e não
precisam de cura. O alvo é o alias de import-time do PRÓPRIO consumidor
(`patch.object(ms._audit_emit, ...)` contra `_lib/memory_shared.py:58`): teste
e consumidor leem a mesma referência, e um rebind de `_lib.audit_emit` não os
separa. **Nada a curar sob cerimônia.**

### 6.1 Oráculo de canonicidade — MEDIDO

O oráculo é `python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>`
(o `_release_tag_guard.py` **não** tem esse modo — sai rc=2). Ele imprime
`<path>\t1` (guarded) ou `<path>\t0` (livre) e **sai rc=0 nos dois casos**:
o veredito é o DÍGITO, nunca o rc. A flag funciona mas **não aparece no
`--help`**.

**Controle antes de confiar** — um oráculo que respondesse `0` para tudo
passaria despercebido na tabela acima, onde todos os 9 dão `0`:

| Path | Dígito | |
|---|:---:|---|
| `PROTOCOL.md` | **1** | controle positivo |
| `.claude/hooks/_lib/audit_emit.py` | **1** | controle positivo |
| `.claude/hooks/_lib/ledger_provenance.py` | **1** | controle positivo |
| `.claude/hooks/check_canonical_edit.py` | **1** | controle positivo |
| `README.md` | 0 | controle negativo |
| path inexistente | 0 | controle negativo (rc=0, sem erro) |

O oráculo **discrimina**. Medido sobre os 29 arquivos do censo: **28 → `0`**,
**1 → `1`** (`.claude/hooks/_lib/tests/test_memory_shared_fence.py`). Os 3
entregáveis desta fase também dão `0`.

> Nota colateral: `CLAUDE.md` responde **`0`**. Isso é **deliberado e
> documentado** em `check_canonical_edit.py:201-203` ("CLAUDE.md is
> intentionally NOT guarded because it is edited every [sessão]... needs a
> separate session-closeout ceremony convention"), não uma lacuna. Vale
> registrar porque é exatamente por isso que o corolário do `CLAUDE.md` §5
> pago na S329 — *enquanto um pack MANIFEST-based espera assinatura, nenhum
> dos seus destinos pré-existentes pode ser editado* — precisa ser convenção
> humana: nenhum guard mecânico o impõe.

---

## 7. Questões abertas (opção conservadora já adotada em cada uma)

- **OQ-1 — subclasse VACUOSA (5 sítios).** Curar o patch faz esses testes
  passarem a exercer o que afirmam, e um deles pode ficar VERMELHO ao ganhar
  visão (o fail-open pode não ser o que se supõe). *Conservador adotado:*
  reportado, não curado; fase 2 decide se entra junto ou vira wave própria.
- **OQ-2 — perf xfail (4 sítios).** A cura muda os números medidos do p99.
  Sendo `xfail(strict=False)` advisory, nenhum gate reprova; mas a série
  histórica de perf muda de significado. *Conservador:* P3, curar só com
  registro explícito de que a série quebra.
- **OQ-3 — `string-target` (16 sítios / 3 arquivos: `test_rag_events.py` 12,
  `test_check_agent_spawn_coverage.py` 3, `test_check_read_injection_coverage.py` 1).**
  `patch("_lib.audit_emit.x")` re-resolve no momento do patch via
  `mock._dot_lookup`, que usa `getattr` no pacote **sem** fallback para
  `sys.modules`: imune à variante stale-rebind, mas levanta `AttributeError`
  sob a variante *dangling package attribute* (documentada em
  `test_tool_lifecycle_observe.py`). *Conservador:* `INDETERMINADO`, não
  `SEGURO`. Fechar exige um segundo poluidor (pop SEM re-import) — **não
  executado nesta fase**.
- **OQ-4 — FECHADA.** O oráculo existe (`check_canonical_edit.py`), foi
  medido com controle positivo e negativo, e confirma a partição:
  cure list inteira livre (`0`), `_lib/tests/` guarded (`1`) mas sem cura
  a fazer. Ver §6.1.
- **OQ-5 — 19 `INDETERMINADO`.** `--strict` sai **rc=1** hoje. Se o
  instrumento for ao CI, precisa de decisão: advisory (rc ignorado) ou
  baseline congelado.

---

## 8. O que o rail provavelmente vai achar

- **Inferência de alvo é conservadora e over-approxima.** `infer_targets`
  toma a UNIÃO dos módulos importados pelo arquivo de teste + heurística de
  nome, e basta UM alvo `call-time` para marcar FRAGIL. Um arquivo que
  importa 3 módulos e patcha o emissor por causa de só um pode ser
  super-reportado. Mitigação: a reprodução é que decide, e ela rebaixou 4
  arquivos. O critério de cada veredito vem impresso.
- **`live-rebind` tem ressalva de ORDEM não fechada.** Um rebind em `setUp`
  só protege sítios executados DEPOIS dele. Em
  `test_spool_drain_rotation_race.py` a segunda classe de teste depende de o
  `setUp` da primeira já ter rebindado o global do módulo. Vale como
  executado hoje; não vale por construção. Está no critério impresso, não no
  veredito.
- **O poluidor cobre UMA variante.** Pop + `delattr` + re-import. A variante
  *dangling* (pop sem re-import) não foi exercida — é a OQ-3.
- **`unmodelled-form` está vazio hoje**, o que significa que toda chamada
  patch-shaped casou uma regra modelada. É o resultado desejado, mas um
  conjunto vazio não prova cobertura: quem prova é
  `test_no_patch_shaped_emitter_mention_escapes_the_census`, que varre a
  árvore real e já reprovou de verdade duas vezes durante esta fase.
- **Escopo.** Só `.claude/hooks/tests/` e `.claude/hooks/_lib/tests/`. As
  outras 11 entradas de `testpaths` do `pytest.ini` não foram varridas, e
  rodam no MESMO worker sob `-n auto`.

---

## 9. Fase 3 — delta pós-rail (S329)

Base: árvore viva pós-`bc8784f` (instrumento endurecido pelo rail). Entrada:
o DELTA que o rail abriu — **3 `FRAGIL` + 30 `INDETERMINADO`**. Nenhum arquivo
canônico tocado; nenhum commit.

| Veredito | Entrada | Saída |
|---|---:|---:|
| `FRAGIL` | 3 | **0** |
| `INDETERMINADO` | 30 | **14** |
| `LOOKUP-VIVO` | 43 | **62** |
| `SEGURO` | 29 | 29 |
| **sítios** | **105** | **105** |

Conservação verificada por arquivo: nenhum sítio inventado, nenhum descartado.

### 9.1 `FRAGIL` (3) — curados, vermelho reproduzido

Os três estão em `test_spool_drain_rotation_race.py`, todos da classe
`SpoolDrainPathRotationRaceTest` (a classe 2), e todos vinham do MESMO defeito
que o rail nomeou: a classe 2 herdava "por acidente" o rebind vivo do `setUp`
da classe 1 e ficava descoberta quando rodava sozinha.

**Cura**: C3 no `setUp` da PRÓPRIA classe (agora `:264-266` — `global
audit_emit, audit_hmac` + `importlib.reload(importlib.import_module(...))`),
idioma copiado do precedente na classe 1 (`:66-68`). Um sítio cura os três.

**Prova (poluidor sintético do §4, classe 2 SOZINHA)**:

```
PYTHONPATH=<tmp>/pollute python3 -m pytest \
  .claude/hooks/tests/test_spool_drain_rotation_race.py \
  -q -p no:cacheprovider -p polluter_plugin -k SpoolDrainPathRotationRace
```

| | resultado |
|---|---|
| VERMELHO (antes) | `1 failed` — `ImportError: module _lib.audit_emit not in sys.modules`, em `setUp:259` |
| VERDE (depois) | `1 passed` |

Controles: sem poluidor `1 passed` nos dois lados; classe 1 sozinha com
poluidor segue `3 passed`; arquivo inteiro com poluidor `4 passed`. O poluidor
imprimiu `old_is_new=False` em todas as execuções (inerte é impossível).

### 9.2 `INDETERMINADO` (30) — triagem por decisão

| Decisão | Sítios | Forma | Desfecho |
|---|---:|---|---|
| **(a)** realmente frágil, vermelho reproduzido | **16** | `string-target` | **curados** (C1) |
| **(b)** seguro, mas o instrumento não prova | **14** | `obj-consumer` (11), `obj-alias` (1), `direct-assign` (2) | **residual justificado** |
| **(c)** alvo não é `_lib.audit_emit` | 0 | — | nenhum sobrou nesta classe |

A separação NÃO veio de leitura: veio de uma segunda variante de poluidor
(§9.3), que reprovou exatamente 16 e deixou 14 verdes.

### 9.3 Decisão (a) — 16 sítios `string-target`: **OQ-3 fechada, e ela era real**

A OQ-3 do §8 dizia que a variante *dangling* não tinha sido exercida. Foi
agora, e é ela que separa a população.

**Mecanismo.** `mock.patch("_lib.audit_emit.X")` resolve por
`mock._dot_lookup` → `getattr(_lib, "audit_emit")`, com um retry
`__import__("_lib.audit_emit")` que é **no-op enquanto o nome ainda está em
`sys.modules`** — logo o atributo do pacote nunca é re-setado e o `getattr`
falha uma segunda vez. Já o consumidor faz `from _lib import audit_emit` (ou
`from _lib.audit_emit import X`), cujo `IMPORT_FROM` **tem** fallback para
`sys.modules`. Teste e consumidor divergem: o consumidor funciona, o patch
levanta `AttributeError`.

**Isto não é hipótese.** O `tearDown` de
`test_check_agent_spawn.py::TestPLAN078Wave1ModelRoutingAdvisory` (`:441-461`)
documenta o incidente em prosa: *"popping sys.modules alone left the package
attribute dangling, so a LATER test module's `mock.patch("_lib.audit_emit.emit_*")`
raised `AttributeError` ... it reddened `test_skill_retrieve_rag_wire`"* no
passo combinado do `validate.yml`. O restauro do atributo naquele `tearDown` é
a mitigação histórica — e é `try/except: pass` fail-open, mantida por
CONVENÇÃO: qualquer teste novo que sombreie o módulo e não restaure reabre a
classe.

**Poluidor variante 2** (`dangling_plugin.py`): garante `_lib.audit_emit`
PRESENTE em `sys.modules` e `delattr(_lib, "audit_emit")`; aborta se o
`delattr` não pegar ou se a entrada de `sys.modules` sumir.

| Arquivo | Sítios | DANGLING antes | DANGLING depois |
|---|---:|---|---|
| `test_rag_events.py` | 12 | **12 failed** / 2 passed | **14 passed** |
| `test_check_agent_spawn_coverage.py` | 3 | **3 failed** / 30 passed | **33 passed** |
| `test_check_read_injection_coverage.py` | 1 | **1 failed** / 20 passed | **21 passed** |

12+3+1 = **16 = exatamente a população `string-target`**. Correspondência 1:1,
com `AttributeError` em todas — o instrumento acertou o critério que imprime.

> Controle interno de graça: os 2 testes que passaram em `test_rag_events.py`
> sob a variante dangling são justamente os que NÃO usam alvo-string
> (`import _lib.audit_emit as ae` e o que anula `sys.modules`). Perna negativa
> no mesmo arquivo.

**Cura**: C1 — helper `_live_audit_emit()` por arquivo (3 helpers) e
`patch.object(_live_audit_emit(), "<attr>", ...)` nos 16 sítios. Os três
consumidores são `call-time` medidos (`rag_events.py:74`,
`check_agent_spawn.py:2749`, `check_read_injection.py:232`), então o helper põe
teste e consumidor na MESMA semântica `IMPORT_FROM`. Todos os 16 eram
context-manager, então a conversão não move a resolução para o import do
arquivo de teste.

Verde nas TRÊS condições depois da cura: base, variante stale, variante
dangling.

**Vacuidade observada de passagem** (não curada — fora da classe, registrada
para quem for ao §5): dos 3 sítios de `test_check_agent_spawn_coverage.py`,
só `test_audit_log_path_fallback_none` (`:48`) depende do patch — os outros
dois afirmam `assertIsNotNone` e passariam com o patch perdido. Idem
`test_check_read_injection_coverage.py:98` (`assertIsNone` sobre um helper que
retorna `None` de qualquer jeito). Sob a variante dangling isso não escondeu
nada, porque a falha é ALTA; sob uma variante silenciosa, esconderia.

### 9.4 Decisão (b) — 14 sítios residuais, cada linha justificada

Todos verdes sob AS DUAS variantes de poluidor. O motivo é o mesmo em todos:
**teste e consumidor ficam stale JUNTOS, no mesmo objeto** — a assimetria que
define a classe (§1) não se forma.

**Prova de execução, não de leitura** (`identity_probe.py`, poluidor abortando
se `old is new`):

| Consumidor | `holds_old` pós-poluição | `holds_new` | patch na própria referência intercepta |
|---|:---:|:---:|:---:|
| `check_anti_ceo_overhead` | True | False | **True** |
| `check_bash_safety` | True | False | **True** |
| `check_ledger_checkpoint` | True | False | **True** |
| `_lib.mcp.canonical_guard` | True | False | **True** |

Isto é o ponto: o consumidor **É** stale — e continua interceptável, porque lê
o próprio global, não `sys.modules`.

| # | Sítio | Forma | Por que o instrumento não prova | Por que é seguro |
|---|---|---|---|---|
| 1-2 | `test_anti_ceo_overhead.py:493,528` | `obj-consumer` | base `hook` vem de `spec_from_file_location`, não de `import` | `check_anti_ceo_overhead.py:116` liga `_audit_emit` no import e lê o global em `:594,:615`; o teste segura o próprio objeto do loader |
| 3-4 | `test_bash_citation_gate.py:551,557` | `obj-consumer` | base `cbs`, mesmo loader | `check_bash_safety.py:233` import-time; leitura do global em `:1190,:1218,:1688` |
| 5-7 | `test_fact_gate_deny_once.py:580,635,657` | `obj-consumer` | base `cbs`, mesmo loader | idem |
| 8-9 | `test_check_ledger_checkpoint.py:136,1043` | `obj-consumer` | base `HOOK`, mesmo loader | `check_ledger_checkpoint.py:174` import-time; leitura em `:1039,:1050` |
| 10-11 | `test_mcp_canonical_guard.py:550,555` | `obj-consumer` | consumidor fora das raízes indexadas (**OQ-6**) | `_lib/mcp/canonical_guard.py` resolve LAZY em `_init_imports` (`:240-256`) e **cacheia no próprio global**; o teste chama `_lazy_init()` ANTES de patchar, e `_IMPORTS_INITIALIZED` impede re-resolução depois |
| 12 | `test_audit_emit_api_contract.py:954` | `obj-alias` | "nenhum módulo sob teste inferido" — o módulo sob teste **é** o próprio `audit_emit` | auto-consistente: `patch.object(audit_emit, "_write_event")` e `audit_emit.emit_generic(...)` passam pelo MESMO alias de nível de módulo (`:954-955`) |
| 13-14 | `test_audit_emit_ghost_action_guard.py:232,237` | `direct-assign` | idem; alvo é DADO (`_KNOWN_ACTIONS`), não emissor | auto-consistente: a atribuição e o `_emit_and_read` (`:177`) usam o mesmo alias importado em `:50` |

**Ressalva honesta sobre 10-11**: `test_audit_emit_called_on_block` embrulha
todo o bloco de patch num `if canonical_guard._audit_emit is not None and
hasattr(...)`. Se o `_lazy_init()` falhasse, a asserção `assertIn(...)` seria
PULADA e o teste passaria vazio. Não é a classe deste censo, mas é vacuidade
condicional na mesma vizinhança.

**Pedidos de modelagem ao autor do instrumento** (nenhum implementado aqui —
o instrumento é read-only nesta fase):

1. **Loader dinâmico como base provável (9 sítios).** `X = <fn>()` onde `<fn>`
   contém `spec_from_file_location(<literal>, <path>)` e `sys.modules[<literal>]
   = mod`: o literal identifica o módulo tão bem quanto um `import`. Fecharia
   a causa (a) do §2.2 sem regra textual — é resolução de NOME, não de forma.
2. **Auto-consistência (3 sítios).** Quando o alvo do patch e a chamada
   exercitada passam pelo MESMO nome de nível de módulo no MESMO arquivo de
   teste, staleness não separa os dois. Regra estrutural, verificável por AST,
   e cobre `obj-alias`/`direct-assign` sobre o próprio `audit_emit`.
3. **Cache lazy sob flag de inicialização (2 sítios).** `global X` dentro de
   uma função guardada por um booleano de módulo é um `import-time-module`
   depois da primeira chamada. Hoje cai em `call-time` ou fora do índice.
4. **OQ-6 continua aberta e agora tem dono nomeado**: `_lib/mcp/` fora do
   índice é o que impede provar 10-11 mecanicamente.
5. **Nova — OQ-9: a variante dangling deveria virar veredito próprio.** Ela
   não é "não provavelmente seguro": é uma classe com vermelho reproduzido,
   distinta da stale-alias. `string-target` merece um rótulo que a nomeie.

### 9.5 Pacote `_lib/tests/` (guarded)

**Vazio.** Os únicos 2 sítios do pacote (`test_memory_shared_fence.py:140,152`)
seguem `SEGURO` e não entraram no DELTA. Nada exige cerimônia nesta fase.

### 9.6 Verificação

| Comando | Resultado |
|---|---|
| `check-stale-module-patch.py --strict` | `rc=1` — **0 `FRAGIL`**, 14 `INDETERMINADO` (regime inalterado por contrato: rc=1 enquanto houver `INDETERMINADO`; é a OQ-5) |
| `check-stale-module-patch.py --json` | `rc=0`, 105 sítios |
| `check-test-env-hygiene.py` | **`rc=0`** — "337 flagged files, all allowlisted" |
| `test_spool_drain_rotation_race.py` | 4 passed |
| `test_rag_events.py` | 14 passed |
| `test_check_agent_spawn_coverage.py` | 33 passed |
| `test_check_read_injection_coverage.py` | 21 passed |
| cruzado `-n 4` (os 4 acima + `test_check_agent_spawn.py` + `test_ledger_provenance.py`) | **194 passed**, `rc=0` |

**Higiene da cadeia VIVA.** Snapshot antes e depois do run cruzado: **delta =
1 linha**, `action=tool_call_lifecycle_recorded`, `session_id=bc917148-eaee`,
`project` preenchido — o hook da própria sessão para a chamada Bash que
envolveu o pytest. Zero `policy_*`, zero `ledger_*`, zero `session_id` vazio.

### 9.7 O que NÃO foi feito

- **Nenhum commit, nenhum `git add`.** 4 arquivos de teste modificados + esta
  seção.
- **Instrumento não tocado** (`check-stale-module-patch.py` e seu teste são
  read-only nesta fase). Os 5 pedidos do §9.4 são para o autor dele.
- **Nenhuma asserção vacuosa curada.** As 4 identificadas (§9.3, §9.4) estão
  registradas, não corrigidas: são a subclasse (b) do §5, e mexer nelas
  ampliaria o diff para fora da classe deste censo.
- **`build_target_index` não ampliado** para `_lib/mcp/` — OQ-6 é decisão de
  escopo do censo, não desta fase.
