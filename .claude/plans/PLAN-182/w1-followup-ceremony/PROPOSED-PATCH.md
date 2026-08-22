> # ⛔ SUPERSEDED (S321, 2026-08-22) — NÃO ASSINE A PARTIR DESTE ARQUIVO
>
> O material canônico desta cerimônia é agora:
>
> - **sentinel:** `.claude/plans/PLAN-182/wave-w1-followup-approved.md`
>   (o caminho mudou porque `PLAN-182/w1-followup-ceremony/approved.md`
>   **não casa** nenhum padrão da união FECHADA de
>   `check_canonical_edit.py:1004-1014` — seria tratado como ÓRFÃO e
>   não-confiável)
> - **patch:** `S321-CEREMONY.patch` (11 arquivos), com `Patch-sha256`
>   amarrado no sentinel
>
> **Por que este arquivo ficou stale em menos de 24 h:** ele foi
> preparado em `8531562`, e o commit `26a39c5` — que veio DEPOIS —
> renomeou e reescreveu o marcador de dívida para asserir COMPORTAMENTO.
> Tudo o que este arquivo diz sobre "o marcador não dispara" e sobre
> removê-lo passou a ser falso: ele **fica vermelho no land** (medido), e
> o pacote novo o **inverte** em guard permanente em vez de deletá-lo.
>
> O escopo também cresceu: de 2 arquivos para 11 — o pacote absorveu a
> atribuição de projeto nos emissores (W2), o fecho da classe M4 (W3) e a
> emenda do ADR-001 que fecha o AC-7. Assinar um lote é mais barato que
> assinar quatro.
>
> Preservado como registro do que se propunha, e porque as PROVAS de
> ordenação (import → coleta → fixture → corpo) que ele documenta
> continuam válidas.

# PROPOSED-PATCH — PLAN-182 W1 follow-up (cura ESTRUTURAL do carrier ADR-001)

> **Status:** material PROPOSTO. Nenhum caminho canônico foi editado na
> preparação deste documento. O patch abaixo é para o Owner aplicar dentro da
> cerimônia canonical-edit, com o sentinel de `SENTINEL-DRAFT.md` assinado.
> Preparado sobre `HEAD = 54da47101ba556af4687a8a49b4000262ba0341a`
> (`closeout(S320)`), 2026-08-21.

## 1. O que este patch fecha

`_lib/runtime_paths.runtime_state_dir()` (PLAN-182 W1) honra
`CLAUDE_PROJECT_DIR_NATIVE` na **maior** precedência — acima do `HOME` que a
camada de isolamento redireciona. Duas enumerações deveriam tê-lo coberto e
nenhuma foi atualizada quando a W1 landou:

- `_lib/test_isolation.py :: AUDIT_DIR_CARRIERS`, cujo próprio comentário diz
  *"the enumeration lives HERE, exactly once"*;
- a lista enumerada de `CEO_*` que `TestEnvContext` **deleta** em `setUp`
  (`_lib/testing.py`), que não inclui o carrier.

A cura hoje é **perimetral**: um `pop` no import do `conftest.py` raiz + `atexit`
(`5fe41f8`). Este patch move a cura para dentro do módulo que **é dono** da
enumeração, para que o `conftest.py` raiz volte a ser um arquivo de bootstrap de
`sys.path` e não a última linha de defesa de tenancy.

## 2. A decisão: REDIRECIONAR ou REMOVER?

**Decisão: REMOVER (`pop`), no import, e NUNCA restaurar dentro do processo.**

### 2.1 O que `_activate_redirect()` faz de fato (leitura, não suposição)

`test_isolation.py:243-265`. Três observações mecânicas decidem a questão:

1. **`AUDIT_DIR_CARRIERS` não redireciona nada por si.** O `SET` vem de
   `audit_carrier_overrides(tmp_root)` (linha 245), que **hardcoda** três chaves
   (`HOME`, `CEO_AUDIT_LOG_DIR`, `CEO_PROJECT_STATE_DIR`) e não itera a tupla.
   Pôr o nome em `AUDIT_DIR_CARRIERS` só o inscreve em `ALL_AUDIT_CARRIERS`, que
   alimenta `snapshot_keys` (linha 233) — ou seja, **snapshot + restore**, não
   redirect. Uma cura por REDIRECT exigiria editar também
   `audit_carrier_overrides()` (a fonte única reusada pela WS-C) **e**
   `TestEnvContext.subprocess_env()`: três superfícies canônicas em vez de duas.
2. **O `CLEAR` itera de verdade.** Linhas 252-253 fazem `os.environ.pop` para
   cada nome de `AUDIT_CLEAR_CARRIERS`. A metade "remover" é executável por
   construção; a metade "setar" não é.
3. **A regra de qual metade usar já está escrita no módulo** (linhas 113-123):
   overrides que o `TestEnvContext` **não** re-aponta por teste devem ser
   LIMPOS, nunca fixados num caminho de sessão, senão a resolução por-teste
   racha. `TestEnvContext` não seta `CLAUDE_PROJECT_DIR_NATIVE` — logo, pela
   regra do próprio módulo, ele pertence à metade CLEAR.

### 2.2 O que cada opção faz com o braço DEFAULT do resolvedor

`runtime_state_dir()` (runtime_paths.py:133-136) retorna `Path(native)`
imediatamente quando o carrier existe. Se o redirect FIXAR o carrier num
caminho de sessão, o topo da cadeia de precedência passa a vencer **sempre** e o
braço default (`HOME` + slug — que o Eixo 1 já isola) fica **inalcançável** para
a suíte inteira. É exatamente o braço que três arquivos de teste hoje precisam
alcançar e por isso excluem o carrier à mão
(`tests/test_injection_salt.py:68`, `tests/test_audit_family_two_projects.py:52`,
`tests/test_runtime_paths.py:106/123/138`). Com CLEAR, o braço default resolve
para dentro do `HOME` redirecionado — isolado e exercitado.

### 2.3 O que NÃO diferencia (analisado e descartado — não use como argumento)

Cheguei a considerar que o REDIRECT mataria a cobertura do `tighten=0700`
(`audit_hmac.py:400-404`, `injection_salt.py:154-158` calculam
`_overridden = any(...)` e passam `tighten=not _overridden`). **É falso:** o
redirect de sessão já seta `CEO_AUDIT_LOG_DIR` e `CEO_PROJECT_STATE_DIR`, que
estão nas MESMAS tuplas — `_overridden` já é `True` na suíte inteira, hoje, com
ou sem este patch. Registro aqui para que a revisão não reintroduza o argumento.

### 2.4 Por que NUNCA restaurar (medido, com controle)

A escrita que vaza acontece no **desligamento do interpretador**, não no import
e não no corpo do teste:

```
antes-do-import:  []
depois-do-import: []
depois-do-exit:   [audit-log.lock, state]
```

(`python3 -c "from _lib import audit_emit"`, com o carrier apontando para um
diretório canário.) Pilha do primeiro import de `_lib.audit_emit` durante o run
que vaza: `injection_salt.get_instance_salt()` → `_register_mint()` →
`from . import audit_emit`.

A/B controlado, dois runs `pytest` filhos idênticos exceto pelo restore:

| braço | restore | canário |
|---|---|---|
| `withrestore` | `os.environ[...] = _SAVED` no teardown do fixture de sessão | `[audit-log.lock, state]` |
| `norestore` | nenhum | `[]` |

Como o teardown do fixture de sessão roda **antes** de `pytest_sessionfinish`,
que roda antes do `atexit`, qualquer restore dentro do processo devolve o
carrier antes da escrita. É a mesma tabela que `tests/unit/test_credential_rotation_emit.py:64-74`
já registra para as outras três variantes.

**Divergência deliberada de dois precedentes:** `conftest.py` (que sai) e
`test_credential_rotation_emit.py` (que fica) restauram via `atexit`. Isso só é
correto por ordenação LIFO — o `pop` é registrado cedo, logo o handler roda
DEPOIS do flush registrado por `audit_emit`. Numa camada de isolamento essa
ordenação é frágil demais para ser load-bearing (basta um plugin importar
`audit_emit` antes do conftest para invertê-la). Aqui não restauramos: a perda é
processo-local e cosmética (um runner que chama `pytest.main()` várias vezes vê
o carrier ficar removido até sair), e está documentada no docstring.

### 2.5 Production code mantém o override, integralmente

Nada neste patch toca `_lib/runtime_paths.py`. O override continua valendo em
produção, e um teste que o exercita continua setando-o para a própria duração
com `mock.patch.dict` (que aplica DEPOIS deste `pop` e restaura sozinho). O que
o patch remove é só o valor **ambiente**, herdado — o mesmo tratamento que
`CEO_AUDIT_LOG_PATH` e companhia já recebem.

## 3. O patch

### 3.1 `.claude/hooks/_lib/test_isolation.py`

```diff
--- a/.claude/hooks/_lib/test_isolation.py
+++ b/.claude/hooks/_lib/test_isolation.py
@@ -54,6 +54,37 @@
 rare test that genuinely exercises the real resolver; the function-scope assert
 skips for it. Zero uses at ship; a ``validate-governance.sh`` grep gate keeps it
 at zero and CODEOWNERS requires security-engineer review to add one.
+
+## Axis 2 — whole-directory overrides (PLAN-182 W1 follow-up)
+
+PLAN-182 W1 gave the family a single resolver
+(``_lib/runtime_paths.runtime_state_dir()``) whose HIGHEST-precedence input is
+``CLAUDE_PROJECT_DIR_NATIVE`` — above the ``HOME`` Axis 1 redirects. An ambient
+value therefore steers runtime state OUT of the isolated tree no matter what
+Axis 1 does. Measured before this cure: a child ``pytest`` run whose only test
+body is ``assert True`` left ``audit-log.lock`` (0 bytes, 0600) and ``state/``
+(0700) in the operator's directory.
+
+Two properties of that escape decide the shape of the cure, and both were
+measured rather than assumed:
+
+1. **The write happens at interpreter shutdown**, not at import and not in the
+   test body. Probe: with the carrier set, ``from _lib import audit_emit``
+   listed the directory as empty BEFORE the import, empty AFTER the import, and
+   holding both entries after the process exited.
+2. **Any restore inside the process re-opens it.** A/B on a standalone child
+   run — clear-then-restore in a session-fixture finalizer left both entries in
+   the canary; clear-and-never-restore left it empty.
+
+So the carrier is CLEARED (never redirected) at MODULE IMPORT time and is
+DELIBERATELY absent from the restore snapshot. Clearing rather than redirecting
+also keeps the DEFAULT arm of ``runtime_state_dir()`` (``HOME`` + slug, which
+Axis 1 already isolates) reachable for the whole suite; pinning the top of the
+precedence chain to a session path would make that arm unreachable and would
+force a matching edit into ``audit_carrier_overrides`` and
+``TestEnvContext.subprocess_env``. Production code keeps the override in full:
+nothing here touches ``_lib/runtime_paths``, and a test that exercises the
+override sets it for its own duration with ``mock.patch.dict``.
 """
 
 from __future__ import annotations
@@ -132,6 +163,18 @@
     "CEO_AUDIT_LOG_ROTATE_BYTES",
     "CEO_AUDIT_HMAC_DISABLE",
 )
+# Whole-directory overrides: carriers that select the ENTIRE runtime-state dir
+# at the TOP of the resolver precedence (``_lib/runtime_paths``, PLAN-182 W1).
+# They are NEUTRALISED at import time and NEVER restored inside the process —
+# see the module docstring, Axis 2, for the two measurements that force both
+# halves of that sentence.
+#
+# Deliberately NOT part of ``ALL_AUDIT_CARRIERS``: membership there means
+# "snapshot me and restore me at session end", and restoring this carrier
+# before interpreter shutdown is exactly the measured re-opening of the escape.
+WHOLE_DIR_OVERRIDE_CARRIERS = (
+    "CLAUDE_PROJECT_DIR_NATIVE",
+)
 # The full carrier surface — used by the WS-C partial-override rejection and by
 # the WS-E grep gate (every carrier must be enumerated in ONE place).
 ALL_AUDIT_CARRIERS = AUDIT_DIR_CARRIERS + AUDIT_CLEAR_CARRIERS
@@ -146,6 +189,36 @@
 LIVE_LOG_SNAPSHOT_VAR = "CEO_AUDIT_LIVE_LOG_PATH_SNAPSHOT"
 
 
+def _neutralize_whole_dir_overrides() -> Dict[str, Optional[str]]:
+    """Pop every whole-directory override and return what was popped.
+
+    Import-time by design. All three conftests import this module while pytest
+    is loading conftests — BEFORE any test module is imported and long before
+    the session fixture body runs (verified: conftest import -> test-module
+    import -> session-fixture body -> test body). A fixture-time pop would sit
+    two steps later than the collection window.
+
+    The returned mapping is diagnostic only. Nothing restores it: the escape's
+    write happens at interpreter shutdown, so a restore anywhere inside the
+    process hands the carrier back before that write. The cost is process-local
+    and cosmetic — a runner that calls ``pytest.main()`` repeatedly sees the
+    carrier stay popped until it exits — and it is the deliberate trade.
+    """
+    popped: Dict[str, Optional[str]] = {}
+    for key in WHOLE_DIR_OVERRIDE_CARRIERS:
+        popped[key] = os.environ.pop(key, None)
+    return popped
+
+
+# Import-time side effect (the ONE in this module) — see the function docstring
+# for why it cannot wait for the session fixture. This module is pytest-only
+# (it imports pytest at the top) and is excluded from adopter installs by
+# scripts/install.sh, so no production hook can reach this line.
+NEUTRALIZED_WHOLE_DIR_OVERRIDES: Dict[str, Optional[str]] = (
+    _neutralize_whole_dir_overrides()
+)
+
+
 def audit_carrier_overrides(root: Path, *, sync_mode: bool = False) -> Dict[str, str]:
     """Return the carrier env vars to SET so the FULL audit/HMAC surface resolves
     under ``root`` (an isolated tmp tree), plus the sticky test signals.
@@ -230,6 +303,9 @@
 
     # 3) Snapshot every carrier + the sticky signals + the snapshot var + the
     #    tooling vars for exact restore at session end.
+    #    WHOLE_DIR_OVERRIDE_CARRIERS is ABSENT from this tuple on purpose: it
+    #    is the one carrier set that must NOT come back before the interpreter
+    #    exits (module docstring, Axis 2, measurement 2).
     snapshot_keys = (
         ALL_AUDIT_CARRIERS
         + (TEST_HARNESS_VAR, SYNC_MODE_VAR, LIVE_LOG_SNAPSHOT_VAR)
@@ -251,6 +327,11 @@
     # CLEAR carriers so a stale-inherited value can never point at the live tree.
     for key in AUDIT_CLEAR_CARRIERS:
         os.environ.pop(key, None)
+    # Re-assert the import-time neutralisation: a plugin, a conftest or an
+    # earlier test may have set a whole-dir override between this module's
+    # import and the first test. Not snapshotted above, so never restored.
+    for key in WHOLE_DIR_OVERRIDE_CARRIERS:
+        os.environ.pop(key, None)
     # Re-export the real PyYAML user-site AFTER the HOME redirect (setdefault so a
     # test that manages its own PYTHONUSERBASE keeps control).
     for key, value in tooling_overrides.items():
```

### 3.2 `.claude/hooks/_lib/testing.py`

```diff
--- a/.claude/hooks/_lib/testing.py
+++ b/.claude/hooks/_lib/testing.py
@@ -122,6 +122,14 @@
                 or key == "CEO_OVERHEAD_ACK"
                 or key == "CEO_SKIP_REAL_REGISTRY_SMOKE"
                 or key == "CEO_SOTA_DISABLE"
+                # PLAN-182 W1 follow-up: the ADR-001 whole-directory override
+                # outranks the HOME this class redirects three lines below, so
+                # an ambient value would send every runtime-state write of this
+                # test outside the sandbox. Under pytest the session layer has
+                # already popped it; under `python -m unittest` this class is
+                # the ONLY isolation there is. Restored by tearDown from the
+                # CLAUDE_* snapshot taken above, like every other steering var.
+                or key == "CLAUDE_PROJECT_DIR_NATIVE"
             ):
                 del os.environ[key]
 
@@ -302,7 +310,14 @@
         # like ``subprocess_env(CEO_AUDIT_LOG_DIR="", HOME="<real>")`` cannot
         # re-open the fallback-to-live path (Codex pair-rail P1).
         tmp_root = str(Path(self._tmp_root).resolve())
-        path_carriers = ("HOME", "CEO_AUDIT_LOG_DIR", "CEO_PROJECT_STATE_DIR") + tuple(
+        # CLAUDE_PROJECT_DIR_NATIVE joins the validated set: it selects the
+        # WHOLE runtime-state dir at the top of the resolver precedence, so a
+        # child carrying one that points outside this test's tree is the same
+        # partial-override vector C3 exists to reject. Zero callers pass it
+        # today (24 subprocess_env call sites, none naming it), so this is a
+        # no-op that states the invariant instead of leaving a hole in it.
+        path_carriers = ("HOME", "CEO_AUDIT_LOG_DIR", "CEO_PROJECT_STATE_DIR",
+                         "CLAUDE_PROJECT_DIR_NATIVE") + tuple(
             c for c in test_isolation.AUDIT_CLEAR_CARRIERS if c.endswith("_PATH")
             or c.endswith("_DIR") or c.endswith("_ERR") or c.endswith("_LOCK")
         )
```

## 4. Justificativa por hunk

| # | arquivo / hunk | o que faz | por que |
|---|---|---|---|
| A | `test_isolation.py` docstring (`@@ -54`) | documenta o Eixo 2 | O módulo é a autoridade do conjunto de carriers; a decisão CLEAR-e-não-restaurar precisa viver ao lado das duas medições que a forçam, senão a próxima sessão "conserta" o restore de volta. |
| B | `test_isolation.py` constante (`@@ -132`) | cria `WHOLE_DIR_OVERRIDE_CARRIERS` | Torna a enumeração completa outra vez ("lives HERE, exactly once"). Tupla separada e **fora** de `ALL_AUDIT_CARRIERS` porque pertencer a ela significa "snapshot + restore" (linha 233), que é precisamente a variante medida como vazadora. |
| C | `test_isolation.py` import-time (`@@ -146`) | `pop` no import, sem restore | Único instante garantidamente anterior ao import dos módulos de teste (ordenação verificada: conftest-import → test-module-import → fixture-de-sessão → corpo). É a relocação 1:1 do que o `conftest.py` faz hoje, para o módulo dono. |
| D | `test_isolation.py` comentário no snapshot (`@@ -230`) | explica a ausência | Sem isso, a próxima revisão lê a omissão como esquecimento e "corrige" — reabrindo o vazamento. |
| E | `test_isolation.py` pop no redirect (`@@ -251`) | reafirma o `pop` | Defesa em profundidade barata para um valor setado ENTRE o import e o primeiro teste (plugin, outro conftest, teste anterior). Idempotente. |
| F | `testing.py` strip no `setUp` (`@@ -122`) | apaga o carrier por teste | Fecha a **janela do corpo do teste** sob `python -m unittest`, onde `TestEnvContext` é a única camada existente. **Não** fecha o resíduo medido (ver §5) — incluído como prevenção, não como cura. |
| G | `testing.py` C3 (`@@ -302`) | valida o carrier em `subprocess_env` | O C3 promete "nenhum carrier de path aponta o filho para fora da árvore deste teste"; sem o override de diretório inteiro a promessa era falsa por omissão. Hoje é no-op: 24 call sites, nenhum passa o carrier. |

## 5. O que este patch NÃO fecha (declarar no sentinel)

**O resíduo `python -m unittest` DIRETO continua.** Simulei o hunk F
(monkeypatch de `TestEnvContext.setUp` popando o carrier depois do `setUp`
original) e medi:

| módulo | com hunk F simulado | canário |
|---|---|---|
| `.claude/hooks/tests/test_injection_salt.py` | `RAN=10 ERRORS=0 FAILURES=0` | `[audit-log.lock, state]` |
| `.claude/hooks/tests/test_audit_family_two_projects.py` | `RAN=14 ERRORS=0 FAILURES=0` | `[audit-log.lock, state]` |

A razão é estrutural: a escrita é no `atexit`, **depois** do `tearDown` ter
restaurado o carrier a partir do snapshot `CLAUDE_*`. E `test_injection_salt.py`
sequer importa `_lib.testing` (usa `unittest.TestCase` + `_IsolatedHomeMixin`),
então nenhuma edição na camada de harness o alcança.

Fechamento possível, **fora** desta cerimônia porque é edição de arquivo de
teste: replicar nos dois módulos o `pop`-no-import que
`tests/unit/test_credential_rotation_emit.py:76-82` já faz. Alternativa: aceitar
o resíduo e declarar `python -m unittest` não suportado (o CI é pytest-only por
construção).

> ⚠️ `CLAUDE.md` §5 hoje afirma que *"o fechamento definitivo é a cerimônia
> canônica sobre os dois `_lib/`"*. A medição acima mostra que essa frase fica
> **falsa** com o land. Se o Owner corrigir §5 no mesmo commit, `CLAUDE.md`
> precisa entrar no Scope e o sentinel precisa ser re-gerado e re-assinado.

## 6. O mesmo commit precisa remover a cura perimetral

Não são caminhos canônicos e **não** estão no meu FILE ASSIGNMENT; ficam aqui
como instrução de land:

1. `conftest.py` — remover o bloco de import-time (linhas ~81-142: o `pop`,
   `_restore_native_carrier`, `atexit.register`). O ARM B da §7 provou que o
   módulo sozinho basta: o conftest do shadow **não** tinha `pop` e o canário
   voltou vazio.
2. `tests/unit/test_runtime_state_sandbox_confinement.py` — remover
   `test_debt_marker_carrier_absent_from_isolation_enumeration` e atualizar o
   docstring do arquivo (os dois primeiros testes CONTINUAM, são o guard real).

> ⚠️ **O marcador de dívida NÃO vai ficar vermelho.** Ele assere
> `assertNotIn("CLAUDE_PROJECT_DIR_NATIVE", test_isolation.AUDIT_DIR_CARRIERS)`,
> e a cura correta **não** põe o nome ali (§2.1). Verificado contra o módulo
> proposto: `NATIVE in AUDIT_DIR_CARRIERS -> False`,
> `NATIVE in ALL_AUDIT_CARRIERS -> False`. Ou seja: o marcador foi ancorado na
> tupla ERRADA (a metade "SET") e teria permanecido verde através da cura que
> ele existia para anunciar — a classe "instrumento verde cuja pergunta
> envelheceu". Ele tem de ser removido **deliberadamente**, não porque disparou.
> Se um marcador equivalente for desejado no futuro, ele deve assertar sobre a
> UNIÃO das tuplas de carriers, não sobre uma delas.

## 7. Evidência medida (tudo rodado nesta preparação)

Árvore-sombra: cópia integral de `.claude/hooks` para o scratchpad, um
`conftest.py` mínimo que importa **apenas** os dois fixtures (sem `pop`), e um
teste cujo corpo é `assert True`.

| braço | `_lib/test_isolation.py` no shadow | resultado | canário |
|---|---|---|---|
| **A (controle negativo)** | original | `1 passed` | `[audit-log.lock, state]` |
| **B (patch proposto)** | proposto | `1 passed` | `[]` |
| **B2** | proposto, teste com `from _lib import audit_emit` em escopo de módulo | `1 passed` | `[]` |

O braço A é o controle positivo do instrumento: sem ele, "canário vazio" não
provaria nada.

Outras medições de baseline (pré-land, no repo real):

- `pytest .claude/hooks/tests/test_live_audit_isolation.py tests/unit/test_runtime_state_sandbox_confinement.py` → `EXIT=0`, **19 passed, 1 skipped**
- canário dos 4 módulos sob `pytest` (cura perimetral ativa) → `EXIT=0`, **53 passed**, canário **vazio**
- `derive-audit-family.py --assert-migrated` → `EXIT=0`, *"0 módulo(s) runtime"*
- `py_compile` nos dois arquivos propostos → OK
- `subprocess_env(` → **24** call sites, **0** passando o carrier

## 8. Observações que NÃO viram patch

- `audit_carrier_overrides()` (linha 162) ainda constrói a árvore isolada com o
  literal legado `.claude/projects/ceo-orchestration`. É inofensivo (é um tmpdir)
  e mudá-lo mexeria em testes que esperam esse caminho — fora de escopo, mas
  vale registrar antes que alguém leia como regressão da W1.
- `test_carrier_set_single_source_complete`
  (`tests/test_live_audit_isolation.py:135-145`) exige um SUBCONJUNTO, não
  igualdade — verificado contra o módulo proposto: continua verde.
