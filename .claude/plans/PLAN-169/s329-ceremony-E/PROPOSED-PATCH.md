# PROPOSED-PATCH — wave-s329-E (PLAN-169): `upgrade.sh` DERIVA o roster de hooks do template

Patch: `.claude/plans/PLAN-169/s329-ceremony-E/E.patch`
Patch-sha256: 9995a27d33c9e82ff0f873d6530501a270d0fc629a5e6c5477de8aad8a78ffc4
Base: ver `BASE-SHA.txt` (o `finalize_patch.py` recusa uma sombra cuja base não
seja o HEAD vivo, e grava o mesmo sha no `Patch-base:` do sentinel)

---

## 1. O quê

Cinco arquivos, dois deles **canônicos**:

| path | +/− | canônico? | papel |
|---|---|---|---|
| `scripts/upgrade.sh` | +366 / −94 | **sim** | a cura: o roster deixa de ser literal e passa a ser derivado do template |
| `.github/workflows/smoke-install.yml` | +61 / −1 | **sim** | 2 entradas de `paths:` + 1 step + `timeout-minutes` 83 → 126 (composto sobre o +15 do PLAN-185 W1+W2) |
| `scripts/tests/test-upgrade-lifecycle-hooks-derived.sh` | +783 / −0 | não | e2e com install e upgrade REAIS (51 asserções) |
| `.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py` | +914 / −0 | não | 49 testes de unidade sobre a FUNÇÃO extraída do `upgrade.sh` shipado |
| `.claude/plans/PLAN-169/s329-ceremony-E/DESIGN-E.md` | +680 / −5 | não | o registro de desenho (§10 = re-derivação por item sobre cc00235) |

> Os números de linha acima são os da sombra no momento em que este registro foi
> escrito. O `finalize-E.sh` re-deriva o patch contra o HEAD vivo e o
> `EXPECTED_PATCH_PATHS` do `EXPECTED-BASELINE.txt` é o conjunto que o G4 do
> LAND compara — é ele, não esta tabela, que decide.

Os três não-canônicos viajam no MESMO patch de propósito. Um teste que landasse
depois da cura seria uma janela em que a classe não tem guarda; e o wiring no
`smoke-install.yml` é canônico, então o teste e o wiring não podem se separar de
jeito nenhum.

## 2. Por quê

`_merge_lifecycle_hooks_into_settings` carregava um roster **literal de 6
registros** dentro do programa `jq`, mais os mesmos 6 repetidos em prosa para o
`--dry-run`. O template `templates/settings/settings.base.json` enumera **47**.

**O achado de origem** (`PLAN-179/s328-ceremony-D/FINDING-upgrade-lifecycle-hooks-S328.md`,
rail codex rodada 3 do pacote D): o registro `PreToolUse` /
`check_ledger_checkpoint.py` **nunca foi registrado por nenhum upgrade**. Um
adopter instalado em v1.0.0 não recebe hoje nenhum hook posterior que não seja
um dos seis.

**O achado que só apareceu ao implementar, e que é a justificativa mais forte
para mudar a SEMÂNTICA junto com a fonte:** extraindo os 6 blocos literais de
`git show HEAD:scripts/upgrade.sh` e comparando com o template campo a campo,
**5 dos 6 DIVERGIAM** (todos no `_comment`; só `Setup` batia). Como o `_reg`
pré-cura RE-CANONICALIZAVA — filtrava o pré-existente e re-appendava o bloco
literal — a sequência real em campo era:

1. `install.sh` entrega o template ⇒ o adopter fica com o `_comment` CORRENTE;
2. o primeiro `upgrade.sh` sobrescreve 5 desses blocos com a cópia ESTAGNADA de
   dentro do upgrader.

A segunda declaração não era só redundante: era **regressiva**. Por isso a
semântica passa a ser ADITIVA — ausente ⇒ appenda o bloco do template; presente
⇒ **preserva byte-idêntico**.

**Por que nenhum instrumento existente pegava isso.** A paridade install/upgrade
compara as duas na MESMA árvore: um roster faltando nas duas é byte-idêntico e
verde. E `test_template_dogfood_parity` compara dogfood contra template, nunca
dogfood contra *o resultado de um upgrade*. O buraco é exatamente entre os dois.

## 3. Como a derivação funciona

| dimensão | antes | depois |
|---|---|---|
| **fonte** | 6 registros literais no programa `jq` | `$SOURCE_DIR/templates/settings/settings.base.json` — o template do checkout que EXECUTA o upgrade (mesma resolução que `_migrate_settings_baseline` já usa). Nunca `$TARGET`. |
| **chave de identidade** | `test("check_foo\\.py")` — substring, sem âncora | todo token `<nome>.py` do `hooks[].command`, casado como token INTEIRO (a classe de caracteres para em `/`, então um path rende o basename; o lookahead impede `check_x.py` casar dentro de `check_xy.py`). Bloco sem `.py` (o `echo` inline do `PostToolUse\|Agent`) é chaveado pelo COMANDO inteiro. |
| **`--dry-run`** | um loop sobre uma SEGUNDA lista, mantida à mão | o mesmo programa `jq` com `--arg mode report`: o anúncio não pode divergir da escrita porque é a mesma redução |
| **atomicidade** | tempfile no mesmo dir + `[[ -s ]]` + `mv` | idem, mais validação `jq -e 'type=="object" and (.hooks\|type)=="object"'` do resultado ANTES do `mv`; e o arquivo **só é aberto para escrita quando falta alguma coisa** (re-run byte-idêntico) |

## 4. Medições feitas para este pacote

Todas na árvore-sombra, com `PYTHONDONTWRITEBYTECODE=1`:

- **Unidade:** `49 passed`, rc 0.
- **e2e:** `RESULT: 51 passed, 0 failed`, rc 0 — medido DUAS vezes de forma
  independente (CEO e pkg-builder), na condição pré-cura, com `E.3a`/`E.3b`/
  `E.9a`/`E.9b` no log e zero SKIP.
- **Roster do template:** `jq '[.hooks | to_entries[] | .value[]] | length'` = **47**.
  O merge derivado entrega os 47 (E.2d/E.2g: nenhum faltando, nenhum inventado).
- **Invariante anti-rot:** a função extraída por âncora tem **311 linhas** e cita
  **0** tokens `<nome>.py`.
- **Wiring:** `test-upgrade-lifecycle-hooks-derived.sh` aparece **3×** no
  `smoke-install.yml` (lista `pull_request`, lista `push`, e o step que executa).
- **`bash -n`** e **`shellcheck -S warning`**: rc 0 nos dois scripts shell.
  Nota: o step de shellcheck do `validate.yml` varre só `.claude/scripts` +
  `.claude/hooks`; `scripts/` fica FORA — o V1 do LAND cobre.
- **`yaml.safe_load`** e **`actionlint`** no `smoke-install.yml`: OK.
- **`check-test-env-hygiene.py`**: 0 violações novas — e ele **pegou uma real**
  durante a implementação (`TestNoSecondRoster` nascera `unittest.TestCase`;
  curado para `TestEnvContext`).
- **`check-ceremony-script.py --json`**: `blocking_unwaived` = 0.

### Controles positivo e negativo

- **RED control (e2e, `E.3`)** — o upgrader **pré-cura**, lido de
  `git show HEAD:scripts/upgrade.sh`, roda contra o MESMO fixture e deixa
  `check_ledger_checkpoint.py` desregistrado: **2 registros faltando contra 0
  do curado**. É a mesma prova que "editar o repo principal e ver quebrar" daria,
  sem editar o repo principal.
- **Controle POSITIVO (e2e, `E.4`)** — um hook sintético
  (`check_zz_synthetic_e4.py`), **inexistente em `upgrade.sh`**, plantado só no
  template de uma cópia da árvore-fonte, É registrado; e a árvore NÃO modificada
  não o registra. Isso discrimina "deriva do template" de "tem uma lista maior".
- **RED control (unidade)** — mirror root com o `upgrade.sh` de `git HEAD`:
  `17 failed, 6 passed`. Entre os vermelhos:
  `test_the_function_names_no_hook_filenames`,
  `test_every_template_registration_lands_on_an_empty_settings` (6 de 47),
  `test_the_function_reads_the_template_from_the_source_checkout`. Os 6 verdes
  contra o pré-cura são honestos: valem nos dois mundos (ex.: preservação de um
  `check_x.py` fora dos seis) — a discriminação deles vem do e2e.
- **Fuzz de fail-safe (`E.8`)** — 8 formas hostis (evento não-array, blocos
  `1`/`"x"`, `hooks` objeto, `command` numérico, `hooks:[null]`, `hooks:[]`,
  `hooks:null`, `{}`): `rc=0` nas 8, em `report` e em `apply`.

## 5. Manifesto ADR-192

**Nenhum** dos 5 paths consta de `.claude/governance/gate-scripts-manifest.txt`
(9 membros). Nenhum bump de sha é devido, e o G5 do LAND prova isso
mecanicamente pela mesma leitura que o hook faz — além de comparar o número de
paths CANÔNICOS contra `EXPECTED_PATCH_CANONICAL_PATHS=2`, para que um patch que
perdesse o `scripts/upgrade.sh` não passe como "zero canônicos, todos
concedidos".

## 6. Rodadas de pair-rail

Registros em `rail-round-*.md` neste diretório. Cada achado foi tratado como
CLAIM: verificado contra o disco, curado na sombra quando real, com pushback
escrito quando falso. A rodada 1 devolveu 3 P2, todos curados:

1. **container falsy EXPLÍCITO lido como ausência** — `"hooks": null` ou um
   evento `null`/`false` eram classificados como ausentes (`== null` e `// []`)
   e substituídos por arrays do template, contra o contrato de preservação
   declarado. Curado com `has(...)` no CONTAINER, nunca `//` no valor.
2. **o e2e nascia CI-dark** (era a OQ-E4) — `scripts/tests/*.sh` roda SÓ no
   `smoke-install.yml`, e nem o step nem os filtros de path o referenciavam.
   Curado no MESMO patch, que é a única forma que fecha.
3. **a asserção de duplicatas era estruturalmente incapaz de falhar** — o
   `_keyset` já emitia `sorted(set(out))`, então o `uniq -d` recebia um fluxo
   deduplicado e vinha sempre vazio. Curado com um fluxo que preserva
   multiplicidade, nos dois lados (bash e Python).

O `OWNER-S329-E-SIGN.sh` recusa assinar se o registro de MAIOR número não
carregar `Rail-Verdict: APPROVE` na sua primeira linha `Rail-Verdict:` — contar
rodadas não é ler o veredito.

Pair-Rail-Reviewed: ver `rail-round-*.md`
