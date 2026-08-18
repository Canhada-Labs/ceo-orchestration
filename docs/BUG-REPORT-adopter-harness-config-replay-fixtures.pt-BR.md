# BUG REPORT — `harness_config_gate` vermelho permanente em instalação adopter

> **Status:** ABERTO — aguardando triagem. Nada foi corrigido, commitado ou empurrado.
> **Origem:** adopter install `42ledger-core` (repo pessoal do maintainer, fora deste checkout), profile `core,fintech`, stack `none`, framework v1.3.0.
> **Data do diagnóstico:** 2026-08-16
> **Reportado por:** sessão CEO do repo adopter (não do framework).
> **Severidade proposta:** média-alta — não quebra nenhum hook em runtime, mas deixa um gate de segurança permanentemente vermelho em **toda** instalação adopter, o que treina o operador a ignorá-lo.
>
> ⚠️ **NÃO TOCAR NO rc.4 EM ANDAMENTO.** Este documento é só registro. No momento do
> diagnóstico o repo do framework estava com `HEAD = 4273d6c` (`release(v1.3.0-rc.4)`),
> working tree suja (`CLAUDE.md` modificado; `PLAN-179`/`PLAN-180`/`PLAN-181` untracked).
> Nenhum desses arquivos foi lido para escrita, alterado ou incluído em qualquer índice.

---

## 1. Resumo em um parágrafo

As 3 fixtures de positive-control do replay do `check_harness_config.py` moram dentro de
`.claude/hooks/tests/`, que o `install.sh` **exclui deliberadamente** do que é entregue ao
adopter. O hook, porém, roda em qualquer instalação e é fail-closed por design: fixture
ausente = RED. O resultado é que **toda instalação adopter nasce e permanece vermelha**
nesse gate, sem ação possível do adopter que não seja pior que o problema. Não é
configuração incorreta do adopter — é uma dependência de artefato dogfood-only por parte
de um gate de escopo universal.

---

## 2. Sintoma observado

`/ceo-boot` no repo adopter, 24 checks Tier-S, 23 verdes e 1 vermelho:

```
| harness_config_gate | red | harness-config gate FAIL (rc=1): [WARN] settings @ .../templates/settings/settings.base.json | 76 |
```

Observação secundária de UX (ver §7): a linha-resumo do `/ceo-boot` mostra apenas o
**primeiro** achado, que aqui é um `[WARN]` inócuo sobre um arquivo de settings ausente.
A causa real do `rc=1` (3 REDs) não aparece no digest. Isso levou a um diagnóstico
inicial errado na primeira sessão em que o problema apareceu (ver §8).

Executando o hook diretamente no adopter:

```
$ python3 .claude/hooks/check_harness_config.py
[WARN] settings @ <adopter-repo>/templates/settings/settings.base.json
    settings file not present — skipped
[RED] replay @ replay:check_canonical_edit.py
    positive-control fixture MISSING (.../.claude/hooks/tests/fixtures/harness-config/replay/canonical_edit_unauthorized.json) — a control that stops firing reddens the run
[RED] replay @ replay:check_bash_safety.py
    positive-control fixture MISSING (.../.claude/hooks/tests/fixtures/harness-config/replay/bash_safety_destructive.json) — a control that stops firing reddens the run
[RED] replay @ replay:check_agent_spawn.py
    positive-control fixture MISSING (.../.claude/hooks/tests/fixtures/harness-config/replay/agent_spawn_named_no_skill_content.json) — a control that stops firing reddens the run

FAIL: 3 RED finding(s) (1 warning(s))
```

---

## 3. Causa raiz — três fatos verificados

**Fato 1 — o hook exige as 3 fixtures e é fail-closed por design.**
`.claude/hooks/check_harness_config.py:146-153`:

```python
#: Behavioral positive controls: (hook file under .claude/hooks/, fixture
#: file under the replay fixtures dir). Every entry is REQUIRED — a missing
#: fixture reddens the run, so a control cannot silently stop firing.
REQUIRED_REPLAY_CONTROLS: Tuple[Tuple[str, str], ...] = (
    ("check_canonical_edit.py", "canonical_edit_unauthorized.json"),
    ("check_bash_safety.py", "bash_safety_destructive.json"),
    ("check_agent_spawn.py", "agent_spawn_named_no_skill_content.json"),
)
```

O fail-closed é **intencional e correto** (ADR-173 / PLAN-153 Wave E): um controle que
para de disparar em silêncio é pior que um controle vermelho. Não se propõe mexer nisso.

**Fato 2 — as fixtures moram numa árvore dogfood-only.**
`.claude/hooks/check_harness_config.py:155-156`:

```python
#: Default replay fixtures location (repo-relative).
REPLAY_FIXTURES_REL = ".claude/hooks/tests/fixtures/harness-config/replay"
```

**Fato 3 — o instalador exclui essa árvore explicitamente.**
`scripts/install.sh:996-1003`:

```
# NOTE (PLAN-003 Phase 0 I-4): hooks/ and scripts/ are installed
# SELECTIVELY — only top-level files + hooks/_lib/ are shipped to
# targets. Framework-internal directories excluded:
#
#   .claude/hooks/tests/      — 89 unit tests for the framework itself
#   .claude/hooks/legacy/     — Sprint 1 bash fallbacks (removed in
#                                Sprint 3 Item C once invariants met)
#   .claude/scripts/tests/    — 74 unit tests for audit-query,
#                                run-skill-benchmark, check-tier-boundaries
```

**Conclusão:** o gate depende de um artefato que o instalador, por decisão de projeto,
nunca entrega. A interseção Fato 2 ∩ Fato 3 é vazia em qualquer adopter.

---

## 4. Prova de que não é drift/configuração do adopter

| Verificação | Resultado |
|---|---|
| `.claude/hooks/tests/` existe no adopter? | **Não** (`ls: No such file or directory`) — exatamente como o instalador pretende |
| Os 3 hooks-alvo existem no adopter? | **Sim** — `check_canonical_edit.py`, `check_bash_safety.py`, `check_agent_spawn.py` todos presentes |
| `check_harness_config.py` sofreu drift no adopter? | **Não** — sha256 **byte-idêntico** ao upstream: `b46d936f51c2762a06d6af65d320ca55b28ed865a2da432fbb54cac17301a287` |
| As fixtures existem no upstream? | **Sim** — 3 arquivos em `.claude/hooks/tests/fixtures/harness-config/replay/` (680 B, 466 B, 667 B; mtime 06/jul/2026) |

Ou seja: hooks instalados e íntegros, hook do gate idêntico ao do framework, e as fixtures
existem — só não são distribuídas. O adopter está exatamente no estado que o instalador
pretendeu produzir.

---

## 5. A contradição de design (o ponto central)

O próprio `validate-governance.sh` **declara a premissa correta** ao explicar por que o
gate PLAN-119 é condicionado à presença da árvore de testes —
`.claude/scripts/validate-governance.sh:1155-1163`:

```
# DOGFOOD-ONLY: this gate enforces the FRAMEWORK's own test-suite isolation. It
# is gated on the presence of the hooks TEST TREE — an INDEPENDENT dogfood shape,
# deliberately NOT the PLAN-119 artifact itself, so that deleting the isolation
# helper is REPORTED rather than silently skipping the whole gate (Codex
# pair-rail P1). Adopter installs / validate-governance FIXTURE trees ship no
# hooks test tree → skip (keeps test_plan_schema_enforcement green).
if [ -d "$REPO_ROOT/.claude/hooks/tests" ]; then
```

Ou seja: **os dois componentes concordam** que o adopter não tem `.claude/hooks/tests/`.
O `validate-governance.sh` tira a consequência disso (skip condicionado). O
`check_harness_config.py` não — ele exige incondicionalmente um artefato que só existe
sob aquela mesma árvore.

Consequência prática importante: **o adopter não tem saída boa.** Criar
`.claude/hooks/tests/` no adopter para satisfazer o `check_harness_config.py` faz o
`validate-governance.sh` passar a tratar o repo como dogfood tree, disparando o bloco
PLAN-119 (exige `_lib/test_isolation.py`, `conftest.py` com
`_ceo_audit_isolation_session`, etc.) e produzindo 4 FAILs novos. Trocar 3 REDs por 4
FAILs num gate mais crítico não é conserto.

---

## 6. Impacto

- **Runtime: nenhum.** Os hooks L1/L2/L3 estão instalados e vivos — no adopter,
  `hook_live_smoke` reporta 43/43 smoke-pass. Nada está desprotegido *agora*.
- **Garantia: degradada.** O que se perde é justamente a prova de que os 3 guards
  **bloqueiam** (`canonical_edit` não autorizado, `bash` destrutivo, spawn sem
  `## SKILL CONTENT`). O positive-control existe para detectar o dia em que um guard
  para de disparar; no adopter ele nunca roda.
- **Ergonômico / cultural — o pior dos três.** Um gate permanentemente vermelho que o
  operador aprende a classificar como "esperado" perde a capacidade de sinalizar um
  problema real. Um vermelho crônico é funcionalmente equivalente a um gate ausente,
  com o custo adicional de ruído em todo `/ceo-boot`.
- **Escopo:** afeta **toda** instalação adopter, não apenas a `42ledger-core`.

---

## 7. Achado secundário (UX do `/ceo-boot`)

O digest do `/ceo-boot` resume o gate pela **primeira linha** da saída do hook. Como a
saída começa por um `[WARN]` inócuo (`settings file not present — skipped`), o digest
reporta o vermelho com uma mensagem que não tem relação com a causa. Sugestão: ao
resumir um check vermelho, priorizar o primeiro achado de severidade **RED**, ou anexar a
contagem (`3 RED / 1 WARN`). Achado independente do bug principal; pode virar item
separado.

---

## 8. Correção de um registro anterior

Na primeira sessão em que isso apareceu no adopter (registrado no `CHANGELOG` do
`CLAUDE.md` da `42ledger-core`), a causa raiz foi descrita como *"o adopter não consegue
satisfazer os dois gates ao mesmo tempo"*. O **sintoma** está correto (§5, parágrafo
final), mas a formulação sugere que o conserto seria o adopter criar a árvore de testes —
e isso é justamente o caminho errado. A causa raiz precisa é a do §3: **um gate de escopo
universal depende de um artefato de escopo dogfood-only**. O `CLAUDE.md` do adopter será
corrigido em separado.

---

## 9. Opções de conserto (para decisão do framework — nenhuma implementada)

### Opção A — mover as fixtures para um caminho distribuível *(recomendada)*

Realocar as 3 fixtures para uma pasta que o instalador já entrega (p.ex. sob
`.claude/hooks/_lib/`, que é explicitamente shipped conforme `install.sh:997`), atualizar
`REPLAY_FIXTURES_REL`, e garantir a cópia no `install.sh`.

- ✅ Preserva o fail-closed integralmente — nenhuma perda de garantia.
- ✅ O positive-control passa a rodar de verdade no adopter, que é onde ele tem mais
  valor (o dogfood já tem a suíte de testes completa cobrindo isso).
- ⚠️ Requer tocar `install.sh` + o hook + provavelmente o drift-manifest — não é
  candidato para entrar no meio de um rc.

### Opção B — o hook detectar modo adopter e degradar para amarelo

Se a árvore de testes não existe, tratar replay como `skipped`/`warn` em vez de `red`.

- ✅ Mudança mínima, contida a um arquivo.
- ❌ Enfraquece exatamente o invariante que o ADR-173 escreveu: *"a control cannot
  silently stop firing"*. Um atacante que apagasse as fixtures obteria silêncio.
- ❌ Não recupera a garantia — só esconde a lacuna.

**Recomendação:** Opção A. A B troca um vermelho honesto por um amarelo que mente.

---

## 10. Escopo do que foi feito nesta sessão

- ✅ Diagnóstico e este documento (arquivo novo, untracked, em `docs/`).
- ❌ **Nenhum** commit, `git add`, push, tag ou alteração de arquivo existente.
- ❌ Nenhum arquivo do rc.4 lido para escrita ou modificado.
- ✅ `docs/` foi escolhido por não ser iterado pelo `validate-governance.sh` (que só
  percorre `docs/playbooks/`, inexistente). `.claude/plans/` foi **evitado
  deliberadamente**: `validate-governance.sh:467-558` valida nome de arquivo e
  subdiretórios contra o PLAN-SCHEMA, e um `PLAN-182` mal-formado reprovaria o gate
  durante o rc.4.
- ✅ Sem links markdown para caminhos internos, para não interagir com o
  `docs-freshness` link-checker.

**Verificação de não-regressão:** `bash .claude/scripts/validate-governance.sh` executado
no repo do framework **antes** desta escrita → `PASS: Governance files validated. Errors: 0
/ Warnings: 63`. Como este arquivo é um `.md` novo em `docs/` fora de qualquer iteração do
validador, o resultado esperado após a escrita é idêntico.

---

## 11. Próximo passo sugerido

Triagem pelo CEO do repo do framework, com a Opção A virando um PLAN próprio **depois**
que o rc.4 fechar. Não há urgência que justifique entrar no rc.4: o impacto em runtime é
nulo e o gate já está vermelho há dias.
