# VERIFICATION-PLAN — como provar a cura DEPOIS do land

> Todos os comandos rodam da raiz do repo
> (`/Users/joaocanhada/canhada-labs/ceo-orchestration`), salvo onde indicado.
> Disciplina obrigatória: **nunca** `pytest | tail` — o exit code seria o do
> `tail` (lição `feedback-pytest-pipe-tail-masks-exit`). Todo gate captura o
> exit de verdade com `> arquivo; echo $?`.

## P0 — Baseline PRÉ-land (já medido nesta preparação, 2026-08-21, `HEAD 54da471`)

Registre estes números; eles são o "antes" contra o qual o "depois" é comparado.

| medição | comando | resultado |
|---|---|---|
| guard + isolamento vivo | `pytest .claude/hooks/tests/test_live_audit_isolation.py tests/unit/test_runtime_state_sandbox_confinement.py -q` | `EXIT=0`, **19 passed, 1 skipped** |
| canário dos 4 módulos (pytest) | ver P1 | `EXIT=0`, **53 passed**, canário **vazio** |
| resíduo `unittest` direto | ver P2 | `test_injection_salt` `Ran 10 OK` canário **2**; `test_audit_family_two_projects` `Ran 14 OK` canário **2** |
| gate da família | `python3 .claude/scripts/derive-audit-family.py --assert-migrated` | `EXIT=0`, *"0 módulo(s) runtime"* |

## P1 — Canário dos 4 módulos sob pytest (o gate principal)

Este é o teste de que a cura estrutural substitui a perimetral: rode **depois**
de o `pop` do `conftest.py` raiz ter sido removido.

```sh
CANARY="$(mktemp -d)"
env -u CEO_AUDIT_LOG_DIR -u CEO_AUDIT_LOG_PATH -u CEO_AUDIT_LOG_ERR \
    -u CEO_AUDIT_LOG_LOCK -u CEO_PROJECT_STATE_DIR \
    CLAUDE_PROJECT_DIR_NATIVE="$CANARY" \
  python3 -m pytest -q -p no:cacheprovider \
    tests/unit/test_credential_rotation_emit.py \
    .claude/hooks/tests/test_runtime_paths.py \
    .claude/hooks/tests/test_injection_salt.py \
    .claude/hooks/tests/test_audit_family_two_projects.py \
  > /tmp/p1.txt 2>&1
echo "EXIT=$?"; tail -3 /tmp/p1.txt
echo "canario=[$(ls -A "$CANARY" | tr '\n' ' ')] count=$(ls -A "$CANARY" | wc -l | tr -d ' ')"
```

**Esperado:** `EXIT=0`, `53 passed`, `count=0`.

**O `env -u` é load-bearing:** sem ele o filho herda os redirects `CEO_AUDIT_*`
do shell/da sessão e o canário volta vazio pelo motivo ERRADO — asserção vácua.
É a mesma razão pela qual `_run_child` em
`tests/unit/test_runtime_state_sandbox_confinement.py:117-133` limpa esses
carriers antes de lançar o filho.

## P2 — `python -m unittest` DIRETO nos 2 que ainda vazam

Rodar de `.claude/hooks` (é assim que os módulos resolvem `_lib`, via
`sys.path.insert` próprio). `unittest discover` é proibido neste repo — lição
`feedback-suite-is-pytest-only-by-construction`.

```sh
cd .claude/hooks
for m in tests.test_injection_salt tests.test_audit_family_two_projects; do
  C="$(mktemp -d)"
  CLAUDE_PROJECT_DIR_NATIVE="$C" python3 -m unittest "$m" > /tmp/p2.txt 2>&1
  echo "$m EXIT=$? -> $(tail -3 /tmp/p2.txt | tr '\n' ' ')"
  echo "  canario=[$(ls -A "$C" | tr '\n' ' ')] count=$(ls -A "$C" | wc -l | tr -d ' ')"
done
cd -
```

**Esperado (resíduo DECLARADO, não regressão):** `Ran 10 ... OK` / `Ran 14 ... OK`
e **`count=2`** (`audit-log.lock`, `state`) nos dois.

Por que continua 2 — medido, não suposto: a escrita acontece no **`atexit`**,
depois de o `tearDown` já ter restaurado o carrier a partir do snapshot
`CLAUDE_*`. Simulei o hunk do `TestEnvContext` (monkeypatch de `setUp` popando o
carrier) e o canário permaneceu 2 nos dois módulos. Além disso,
`test_injection_salt.py` nem importa `_lib.testing` — usa `unittest.TestCase` +
`_IsolatedHomeMixin` —, então nenhuma edição na camada de harness o alcança.

**`count=0` aqui seria surpresa, não vitória:** investigue antes de comemorar
(provavelmente o carrier não chegou ao processo, ou você está listando um
diretório diferente do que passou no env).

Fechamento possível do resíduo, **fora** desta cerimônia (é edição de arquivo de
teste, não de caminho canônico): replicar nos dois módulos o `pop`-no-import
documentado em `tests/unit/test_credential_rotation_emit.py:76-82`.

## P3 — O guard comportamental

```sh
python3 -m pytest -q -p no:cacheprovider \
  tests/unit/test_runtime_state_sandbox_confinement.py > /tmp/p3.txt 2>&1
echo "EXIT=$?"; tail -3 /tmp/p3.txt
```

**Esperado:** `EXIT=0`, **2 passed** — `test_ambient_carrier_does_not_redirect_runtime_state`
e o seu controle `test_control_canary_is_reachable_and_writable_by_the_child`.

### AVISO — `test_debt_marker_carrier_absent_from_isolation_enumeration` NÃO fica vermelho

O enunciado desta cerimônia (e `CLAUDE.md` §5) diz que este caso "fica VERMELHO
no dia em que a cura estrutural landar". **Ele não fica.** Ele assere

```python
assertNotIn("CLAUDE_PROJECT_DIR_NATIVE", test_isolation.AUDIT_DIR_CARRIERS)
```

e a cura correta **não** põe o nome em `AUDIT_DIR_CARRIERS` — essa tupla é a
metade "SET" da enumeração e não redireciona nada por si (ver
`PROPOSED-PATCH.md` §2.1). Verificado contra o módulo proposto:

```
AUDIT_DIR_CARRIERS = ('HOME', 'CEO_AUDIT_LOG_DIR', 'CEO_PROJECT_STATE_DIR')
NATIVE in AUDIT_DIR_CARRIERS -> False
NATIVE in ALL_AUDIT_CARRIERS -> False
```

A consequência operacional não muda: **o caso tem de ser removido no MESMO
commit**, junto com o bloco import-time do `conftest.py` raiz — só que
**deliberadamente**, porque a premissa dele ("a cura é perimetral") ficou falsa,
e **não** porque disparou. Ele foi ancorado na tupla errada e teria seguido verde
através da cura que existia para anunciar — a classe
`feedback-instrument-green-with-stale-question`. Se um marcador equivalente for
desejado no futuro, ele deve assertar sobre a UNIÃO das tuplas de carriers.

Sanity check de um comando (rode DEPOIS do land):

```sh
python3 -c "import sys; sys.path.insert(0,'.claude/hooks'); from _lib import test_isolation as t; \
print('DIR   =', t.AUDIT_DIR_CARRIERS); print('WHOLE =', t.WHOLE_DIR_OVERRIDE_CARRIERS); \
print('NATIVE in ALL ->', 'CLAUDE_PROJECT_DIR_NATIVE' in t.ALL_AUDIT_CARRIERS)"
```

## P4 — Controle POSITIVO (o instrumento vê o defeito?)

Um canário vazio só prova algo se a mesma sonda, contra o código ANTIGO, voltar
cheia. Receita da árvore-sombra (roda fora do repo, não toca nada):

```sh
SH="$(mktemp -d)"
cp -R .claude/hooks "$SH/hooks"
mkdir -p "$SH/run"
printf 'import sys\nsys.path.insert(0, "%s/hooks")\nfrom _lib.test_isolation import (  # noqa: F401\n    _ceo_audit_isolation_session,\n    _ceo_audit_isolation_check,\n)\n' "$SH" > "$SH/run/conftest.py"
printf 'def test_trivial():\n    assert True\n' > "$SH/run/test_trivial.py"

# ARM A — controle NEGATIVO: versão PRE-land do módulo dentro do shadow
git show <SHA-PRE-LAND>:.claude/hooks/_lib/test_isolation.py > "$SH/hooks/_lib/test_isolation.py"
CA="$(mktemp -d)"
( cd "$SH/run" && CLAUDE_PROJECT_DIR_NATIVE="$CA" python3 -m pytest -q -p no:cacheprovider test_trivial.py >/dev/null 2>&1 )
echo "ARM A canario=[$(ls -A "$CA" | tr '\n' ' ')]"

# ARM B — módulo pós-land
cp .claude/hooks/_lib/test_isolation.py "$SH/hooks/_lib/test_isolation.py"
CB="$(mktemp -d)"
( cd "$SH/run" && CLAUDE_PROJECT_DIR_NATIVE="$CB" python3 -m pytest -q -p no:cacheprovider test_trivial.py >/dev/null 2>&1 )
echo "ARM B canario=[$(ls -A "$CB" | tr '\n' ' ')]"
```

**Esperado:** ARM A = `[audit-log.lock state]`, ARM B = `[]`.

O `conftest.py` do shadow **não tem `pop`** — é isso que prova que o módulo
sozinho basta e que o `conftest.py` raiz pode perder o bloco. Foi exatamente
este A/B que rodei na preparação, com o patch proposto no lugar do ARM B.

Se ARM A voltar vazio, a sonda está morta: provavelmente o `cp -R` não pegou o
módulo antigo, ou o `pycache_prefix` do macOS está servindo bytecode antigo
(lição `feedback-macos-pycache-prefix-invalidates-land-sims`) — nesse caso rode
com `PYTHONDONTWRITEBYTECODE=1` e refaça.

## P5 — Suítes e gates (equivalentes ao CI)

```sh
# 1) raizes de teste v1.0.1 (validate.yml, "PLAN-152 tests-01")
python3 -m pytest tests/unit .claude/hooks/_lib/tests .claude/scripts/swarm/tests \
  .claude/scripts/replay/tests tests/test_federation .claude/scripts/mcp-server/tests \
  .claude/scripts/detectors/tests .claude/scripts/predict-budget/tests \
  tests/forensic tests/synthetic \
  -n auto -m 'not serial' --strict-markers --tb=no -q > /tmp/p5a.txt 2>&1; echo "EXIT=$?"; tail -3 /tmp/p5a.txt

python3 -m pytest tests/unit .claude/hooks/_lib/tests .claude/scripts/swarm/tests \
  .claude/scripts/replay/tests tests/test_federation .claude/scripts/mcp-server/tests \
  .claude/scripts/detectors/tests .claude/scripts/predict-budget/tests \
  tests/forensic tests/synthetic \
  -m 'serial' --strict-markers --tb=no -q > /tmp/p5b.txt 2>&1; echo "EXIT=$?"; tail -3 /tmp/p5b.txt

# 2) hook tests (os dois passes do CI)
python3 -m pytest .claude/hooks/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q > /tmp/p5c.txt 2>&1; echo "EXIT=$?"; tail -3 /tmp/p5c.txt
python3 -m pytest .claude/hooks/tests/ -m 'serial' --strict-markers --tb=no -q > /tmp/p5d.txt 2>&1; echo "EXIT=$?"; tail -3 /tmp/p5d.txt

# 3) scripts tests
python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q > /tmp/p5e.txt 2>&1; echo "EXIT=$?"; tail -3 /tmp/p5e.txt

# 4) gate de governanca (inclui o gate WS-A/C/E do PLAN-119, que checa os 3 conftests)
bash .claude/scripts/validate-governance.sh > /tmp/p5f.txt 2>&1; echo "EXIT=$?"; grep -n "audit-isolation" /tmp/p5f.txt | head

# 5) gate da familia por projeto
python3 .claude/scripts/derive-audit-family.py --assert-migrated > /tmp/p5g.txt 2>&1; echo "EXIT=$?"; tail -2 /tmp/p5g.txt
```

**Esperado:** todos `EXIT=0`. Dois alvos merecem atenção nominal:

- `.claude/hooks/tests/test_live_audit_isolation.py::test_carrier_set_single_source_complete`
  exige um SUBCONJUNTO em `ALL_AUDIT_CARRIERS` (não igualdade). Verificado
  contra o módulo proposto: continua verde.
- O gate WS-A/C/E do `validate-governance.sh` (linhas ~1163-1177) exige a string
  `_ceo_audit_isolation_session` nos **três** conftests. Remover o bloco
  import-time do `conftest.py` raiz **não** remove esse import — se for removido
  por acidente, o gate fica vermelho, e é o comportamento certo.

## P6 — Delta do log VIVO (o que a cura NÃO promete)

A cura remove o carrier; ela não impede que uma escrita de `atexit` — depois de
o teardown da sessão ter devolvido o `HOME` real — resolva para o diretório
VIVO. Isso é condição PRÉ-existente do WS-A, não algo introduzido aqui, mas meça
o delta para não confundir uma coisa com a outra:

```sh
LIVE="$HOME/.claude/projects/-Users-joaocanhada-canhada-labs-ceo-orchestration/audit-log.jsonl"
before=$(wc -l < "$LIVE" 2>/dev/null || echo 0)
python3 -m pytest .claude/hooks/tests/test_live_audit_isolation.py -q -p no:cacheprovider > /tmp/p6.txt 2>&1; echo "EXIT=$?"
after=$(wc -l < "$LIVE" 2>/dev/null || echo 0)
echo "delta_linhas_log_vivo=$((after - before))"
```

**Esperado:** `EXIT=0` e `delta=0`. Um delta > 0 **não** é falha desta cerimônia
— é achado novo, a ser aberto separadamente. E `test_live_audit_isolation` flaka
sob sessão concorrente (lição
`feedback-live-audit-isolation-flakes-under-concurrent-session`): meça o delta,
não o verde/vermelho isolado.

## P7 — Critérios de falha e rollback

| sintoma | leitura | ação |
|---|---|---|
| P1 `count>0` | a cura estrutural não está ativa (o import não fired, ou o `pop` do conftest saiu antes do land dos `_lib/`) | não commite; verifique a ordem do commit |
| P4 ARM A vazio | sonda morta | conserte a sonda antes de acreditar em qualquer verde |
| P2 `count>2`, ou módulos novos vazando | regressão real | `git revert` do commit; o resíduo declarado é exatamente 2 entradas em 2 módulos |
| P5 vermelho em `test_live_audit_isolation` | possivelmente a flaka conhecida | re-rode isolado + meça o delta de P6 antes de tratar como regressão |
| P3 com 3 passed | o marcador de dívida não foi removido | remova-o no MESMO commit (ver o AVISO em P3) |

**Rollback:** o patch é aditivo e local aos dois `_lib/`; `git revert` do commit
restaura o estado anterior. Se o revert for necessário DEPOIS de o `conftest.py`
ter perdido o `pop`, ele precisa restaurar as duas coisas juntas — senão a
árvore fica sem cura nenhuma, que é pior que o estado atual.
