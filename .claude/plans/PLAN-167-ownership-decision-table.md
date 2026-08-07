---
id: PLAN-167
title: Tabela de decisão de propriedade — sair do loop de patch-por-ramo no F3
status: reviewed
created: 2026-08-06
reviewed_at: 2026-08-06
owner: CEO
depends_on: [PLAN-166]
budget_tokens: 180-260k
budget_sessions: 1-2
context_risk: high
external_wait: assinatura GPG do Owner (manhã) para o land do pack
tags: [upgrade, install, ownership, testing, canonical, refactor]
---

# PLAN-167 — Tabela de decisão de propriedade

> **Ratificação (2026-08-06, S296).** Owner instruiu, textualmente:
> *"escreve o PLAN-167 pra resolver tudo isso de uma vez… deixa o plano
> pronto para ser executado"* e *"já deixa o plano perfeito e pronto pra
> executar"*. `draft → reviewed` registrado com base nessa instrução.
> **`reviewed` ratifica o PLANO — não libera edição canônica.** Todo
> arquivo guardado continua atrás da cerimônia GPG do W5.

> **Origem.** Este plano nasce de um loop observado, não de uma ideia.
> Na S296 o rail codex rodou **11 rodadas** sobre o F3 do PLAN-166
> (propriedade por registro de entrega). Resultado: **20 achados reais
> aplicados, 4 ainda abertos, zero sinal de convergência** — e cerca de
> metade dos achados recentes eram **regressões do fix da rodada
> imediatamente anterior**. O e2e de 45 checks passou verde durante os
> 20. Este plano ataca a causa, não mais uma célula.

---

## 0. Primeira hora (checklist literal do run)

Faça nesta ordem. Não pule para o W2 — a tabela é o produto, o refactor
é consequência dela.

1. `git rev-parse HEAD` → deve ser `516e64e…`. Se não for, PARE e
   reporte: o estado inicial mudou e este plano assume o de S296.
2. `git status --porcelain` → esperado sujo com grupo A + F3 (S296).
   **Não limpe, não faça `git checkout -- .`, não `git stash`.**
3. Ler, na íntegra, os 11 vereditos:
   `.claude/plans/PLAN-166/archive/codex-review-w1-{ceremony,round2..round11}.md`.
   São a documentação mais densa do espaço que existe.
4. Ler `.claude/plans/PLAN-166/W1-ceremony-log.md` §"Rounds 6-9" e
   §"Follow-ups nomeados".
5. Ler `ADR-155` + `ADR-155-AMEND-1`.
6. Só então começar o W0.1.

---

## 1. Diagnóstico (o porquê do loop)

O F3 é um **produto cartesiano** implementado como `if` espalhado:

| Dimensão | Valores |
|---|---|
| `surface` | `spec` (`SPEC/v1`) · `protocol` (`PROTOCOL.md`) · `marker` (`.claude/.framework-version`) |
| `prior_record` | `none` · `hash` · `link_match` · `link_retargeted` |
| `live_type` | `absent` · `dir` · `regular` · `symlink` · `special` (FIFO/socket) · `dir_empty` |
| `live_content` | `pristine` (== fonte) · `edited` · `legacy_pristine` (fingerprint v1.2−) |
| `source_has` | `yes` · `no` (downgrade `--pin` pré-v1.3) |
| `mode` | `copy` · `link` |
| `ceremony` | `user` · `maintainer` |
| `operation` | `install_fresh` · `install_rerun` · `upgrade` |
| `skip_requested` | `none` · `self` · `descendant` |

Três consequências, todas verificadas na S296:

1. **Sem especificação executável.** "Correto" é decidido ramo a ramo.
   Ramos diferentes codificam premissas **contraditórias sobre a mesma
   pergunta** — por isso consertar A quebra B.
2. **Decisão duplicada entre `install.sh` e `upgrade.sh`.** A classe
   "irmão atrasado" foi **4 dos 20 achados** — 20%.
3. **O e2e não cobre o espaço.** 45 checks lineares, 8 cenários. O rail
   virou o único explorador: **uma célula por rodada de ~40 min.**

**Anti-objetivo explícito:** este plano NÃO é "corrigir os 4 achados
abertos do round 11". Corrigir ramo a ramo É o loop. Os 4 abertos, como
os 20 aplicados, viram **linhas da tabela**.

---

## 2. A solução (5 movimentos)

1. **Escrever a tabela.** Onde as contradições aparecem ANTES de virar bug.
2. **Fechar o veredito num enum pequeno**, derivado da tabela, nunca de
   memória ([[feedback-closed-sets-must-be-derived-not-recalled]]).
3. **UMA função decide.** `_ownership_verdict()`. `install.sh` e
   `upgrade.sh` param de decidir e passam a **executar**.
4. **A tabela vira a suíte.** Fix que quebra outra célula falha na hora.
5. **O rail revisa a TABELA, não o diff.** Espaço finito ⇒ converge.

### 2.1 Enum de veredito (rascunho — o debate do W1 ratifica ou emenda)

```
DELIVER          — escrever a versão do framework no alvo
REFRESH          — substituir conteúdo existente (backup-then-replace)
PRESERVE_OWNED   — não tocar; MANTER o registro de entrega
PRESERVE_UNOWNED — não tocar; NÃO registrar (adotante é dono)
OMIT_RECORD      — alvo permanece; registro sai do manifesto
ABORT_SURFACE    — recusar esta superfície, rc 0, warning nomeado
```

Segundo campo, ortogonal — **de onde sai o hash do manifesto**:

```
HASH_TARGET | HASH_SOURCE | HASH_PRIOR_RECORD | HASH_CANONICAL_POINTER | HASH_NONE | LINK_RECORD
```

O par `(verdict, hash_source)` é a saída completa. **Todo bug da S296
foi uma célula com o par errado.** `FMS_HASH_ROOT_PATHS` e
`FMS_LINK_PATHS`, criados na S296, são casos particulares que o campo
`hash_source` explícito **substitui** — não somar, substituir.

---

## 3. Fronteira canônica (verificada 2026-08-06)

| Superfície | Guard | Quem escreve |
|---|---|---|
| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | só sob sentinel |
| `scripts/_framework_manifest_set.sh`, `scripts/_hash_lib.sh` | 🔒 | só sob sentinel |
| `.claude/adr/ADR-*.md`, `.github/workflows/*.yml` | 🔒 | só sob sentinel |
| `scripts/tests/**` | ✅ livre | run autônomo |
| `docs/**`, `.claude/plans/**` (exceto `spec.md`) | ✅ livre | run autônomo |

**Consequência de projeto:** a tabela e a suíte inteira nascem em
superfície LIVRE e **podem ser commitadas pelo run** (foi assim no W0 do
PLAN-166). O refactor dos 4 guardados é desenvolvido em **clone overlay**
(padrão S279) e entregue como pack staged. O Owner assina **uma vez**.

---

## 4. Ondas

### W0 — Tabela + suíte (LIVRE, sem sentinel, COMMITÁVEL)

#### W0.1 — `docs/ownership-decision-table.md`

Prosa: as 9 dimensões, a **regra de poda** (abaixo), o par de cada
célula não-óbvia com justificativa, e as perguntas abertas.

**Fontes de entrada, nesta ordem de autoridade:**
1. os **11 vereditos do codex** — cada achado é uma célula com veredito conhecido;
2. o ramo vivo hoje em `install.sh`/`upgrade.sh` (o que o código faz);
3. `ADR-155` + `ADR-155-AMEND-1` (a intenção declarada).

Onde 1, 2 e 3 discordarem: **registrar como pergunta aberta e levar ao
debate do W1.** Não resolver sozinho.

**Regra de poda (obrigatória — sem ela o espaço explode):** uma célula é
ILEGAL quando a combinação não pode existir num alvo real. Declarar cada
regra de poda com o motivo, no doc. Exemplos que já se sabe:
- `operation=install_fresh` ⇒ `prior_record=none` e `live_type=absent`
- `prior_record=link_*` ⇒ `mode=link`
- `surface=protocol` ⇒ `live_type ∈ {absent, regular, symlink}` (nunca `dir`)
- `skip_requested=descendant` ⇒ `surface=spec` (só ele é árvore)
- `ceremony=user` ⇒ `surface ∈ {marker}` para entrega; `spec`/`protocol`
  só aparecem como resíduo de instalação maintainer anterior

Poda silenciosa é proibida: toda combinação removida sai **nomeada**.

#### W0.2 — `scripts/tests/ownership_table.tsv` (FONTE ÚNICA)

TSV com cabeçalho, uma linha por célula legal. Colunas, nesta ordem:

```
id  surface  prior_record  live_type  live_content  source_has  mode
ceremony  operation  skip_requested  expect_verdict  expect_hash_source
origin  note
```

- `id` — estável, `OWN-0001`… (o teste referencia por id; nunca por linha).
- `origin` — de onde a linha veio: `r7-F2`, `r11-F1`, `adr-155`, `derived`.
  **Os 20 achados aplicados e os 4 abertos DEVEM aparecer aqui pelo id do
  round** (é o AC-5).
- `note` — só quando o veredito não é óbvio.

O doc do W0.1 explica; **o TSV é a verdade**. Nenhum valor duplicado
entre os dois.

#### W0.3 — `scripts/tests/test-ownership-table.sh` (gerador + runner)

**Contrato de observação** — como o veredito é observado sem parsear
prosa. Para cada linha: montar fixture, capturar o estado ANTES, rodar o
script REAL, capturar o estado DEPOIS, e derivar:

*`verdict` observado*, de (estado do alvo, manifesto):

| Alvo depois | Manifesto depois | ⇒ verdict |
|---|---|---|
| conteúdo == fonte, não existia antes | tem registro | `DELIVER` |
| conteúdo == fonte, existia e mudou, cópia em `BAK_DIR` | tem registro | `REFRESH` |
| byte-idêntico ao ANTES | tem registro | `PRESERVE_OWNED` |
| byte-idêntico ao ANTES | sem registro | `PRESERVE_UNOWNED` |
| byte-idêntico ao ANTES | registro sumiu (havia antes) | `OMIT_RECORD` |
| byte-idêntico ao ANTES + warning nomeado + rc 0 | sem registro | `ABORT_SURFACE` |

*`hash_source` observado*: o harness calcula os 4 candidatos —
`sha256(alvo_depois)`, `sha256(fonte)`, digest do registro anterior,
hash canônico do ponteiro — e vê **qual deles** o manifesto gravou. Se
o registro for `LINK  …`, `hash_source = LINK_RECORD`. Se não houver
registro, `HASH_NONE`. **Ambíguo** (dois candidatos iguais) ⇒ o harness
DIFERENCIA os fixtures até desempatar; nunca "resolve" por preferência.

Requisitos duros do harness:
- roda os scripts **REAIS**; zero mock do sujeito sob teste
  ([[feedback-livefire-catches-what-fixtures-miss]]);
- fixture em `mktemp -d`, nunca em `$HOME` nem no repo;
- **timeout por célula** (`timeout 60`) — o achado do FIFO no round 9 era
  literalmente um `cp` que pendura;
- `--only <id>` para rodar uma célula; `--map` para emitir o mapa;
- saída determinística e ordenada por `id`.

#### W0.4 — Mapa-baseline

Rodar a suíte contra a árvore ATUAL (com os 20 fixes) e gravar
`scripts/tests/ownership-baseline-map.txt`: por `id`, verde/vermelho e o
par observado vs esperado. Vermelho é **esperado** aqui — é o ponto de
partida e a métrica de progresso do W2.

#### W0.5 — Commit (superfície livre)

```
git add docs/ownership-decision-table.md \
        scripts/tests/ownership_table.tsv \
        scripts/tests/test-ownership-table.sh \
        scripts/tests/ownership-baseline-map.txt \
        .claude/plans/PLAN-167-ownership-decision-table.md
git commit -m "plan(PLAN-167): tabela de decisão de propriedade + suíte gerada + mapa baseline"
```

**Adds explícitos, NUNCA `git add -A`** — a árvore tem canônicos sujos.

**Gate W0:** a suíte roda, produz o mapa, e o commit contém **só** os 5
paths acima (`git show --stat HEAD` confere).

### W1 — Debate L3 (obrigatório, PROTOCOL.md)

`/debate start PLAN-167 "tabela de decisão + função única de veredito"`

Arquétipos a convocar (routing de `.claude/team.md`): **qa-architect**
(a suíte é o coração), **security-engineer** (apagar conteúdo do
adotante é a consequência das células erradas — dois P1 do round 9 eram
isso), **devops** (install/upgrade são superfície de distribuição).

Pauta fechada em 3 pontos:
1. **O enum é o certo?** 6 vereditos + 6 fontes-de-hash cobrem as células
   sem forçar nenhuma? Falta? Sobra?
2. **As perguntas abertas do W0.1** (onde codex/código/ADR discordam).
3. **Assinatura e domicílio da função.** Uma lib NOVA seria um path
   canônico novo → exige entrada em `_CANONICAL_GUARDS` → **cerimônia de
   kernel**. Preferir `scripts/_framework_manifest_set.sh` (já guardado)
   salvo veto fundamentado; veto escala ao Owner de manhã, não vira
   cerimônia de kernel no meio da noite.

**Saída:** `debate/round-{1,2,3}/consensus.md` (livre) + `ADR-190` em
`staged/` (ADR é guardado — não escrever em `.claude/adr/`).

### W2 — Implementação em clone overlay

```
CLONE="$SCRATCH/plan167-overlay"
git clone --local . "$CLONE"        # pega o commit do W0.5
cd "$CLONE" && git checkout -b plan167-refactor
```

Trabalhar **só** ali. A árvore viva não recebe edição canônica — é a
regra 1 do §6.

- **W2.1** Implementar `_ownership_verdict()` conforme o consenso do W1.
- **W2.2** Refatorar `install.sh`/`upgrade.sh` para **chamar e executar**
  o veredito. Os ramos de decisão antigos SAEM.
- **W2.3** `_framework_manifest_set.sh` passa a receber `hash_source`
  explicitamente. `FMS_HASH_ROOT_PATHS`/`FMS_LINK_PATHS` são removidos —
  substituídos, não somados.
- **W2.4** Dirigir o mapa até **100% verde**. Regressão em célula já
  verde = **para e corrige antes de seguir** (esse é o mecanismo que
  substitui o loop de 40 min).
- **W2.5** Gates completos no clone: e2e F3 45/45, bateria
  `python3 -m pytest .claude/scripts/tests/ -q`, `shellcheck -S warning`,
  `bash -n`.

**Gate W2:** mapa 100% verde **e** toda linha com `origin` de round
(os 20 + os 4) verde.

### W3 — Rail codex sobre a TABELA (limitado por construção)

Alvo da revisão muda — é a diferença central em relação à S296.

```
cd "$CLONE"
caffeinate -dims nohup codex exec review --uncommitted </dev/null \
  > .../codex-plan167-r1.md 2>&1 &
```

Pergunta ao rail: *"algum veredito desta tabela está errado, e falta
alguma célula legal?"* — não "revise o diff".

**Esperar pelo ARTEFATO, nunca por processo:**
`until [ -s "$OUT" ]; do sleep 15; done`. Um `until ! pgrep -f "codex …"`
**nunca termina** — casa o próprio waiter
([[feedback-pgrep-waiter-matches-itself]]).

**Regra de parada (dura, aprendida na S296):**
- APPROVE, **ou**
- 2 rodadas consecutivas sem achado novo, **ou**
- **teto de 4 rodadas** — atingido, o run **PARA e reporta**. Não
  patcheia mais. Sob nenhuma hipótese entra na 5ª.

Todo achado do rail vira **linha de tabela** → suíte re-roda → mapa
volta a 100%. Achado que não couber como linha é **furo do MODELO**:
registrar e levar ao Owner, não remendar.

### W4 — Montagem do pack (staged, sem assinar)

- `.claude/plans/PLAN-167/staged/` com cópias dos guardados + patches + `ADR-190`
- `staged-manifest.sha256` **rastreado**
  ([[feedback-staged-inputs-need-tracked-hash-manifest]])
- `W4-approved-draft.md`: Scope em grupos de revert (**grupo A do
  PLAN-166 + os guardados do PLAN-167**) e `Anchor-SHA: <PLACEHOLDER>`
  — inassinável de propósito
- `W4-land-runbook.md`: applies, gates, §touched−scope, commit.
  **Snippets em POSIX** — `[[:space:]]`, nunca `\s` (BSD não suporta; o
  §7 do PLAN-166 devolvia falso "tudo fora de escopo")
- `OWNER-W4-LAND.sh` cobrindo **todo** path do staged, com espelhamento
  por **tabela path→patch**, nunca lista manual

**Gate W4 (automatizado, não a olho):**
- `shasum -c staged-manifest.sha256` rc=0 (rodar **da raiz** — os paths
  são repo-relative)
- `git apply --check` em todo patch
- diff automatizado **staged-vs-script-de-land**: todo arquivo staged
  aparece no `OWNER-W4-LAND.sh` (a omissão de `_parity_classify.py` foi
  o achado F3 do round 8)

### W5 — Manhã do Owner (não-autônomo)

1. Ler o sumário e o `W4-approved-draft.md`
2. Fixar `Anchor-SHA` = HEAD e assinar (`gpg --detach-sign --armor`;
   se der "No pinentry": `export GPG_TTY=$(tty); gpgconf --kill gpg-agent`)
3. `bash OWNER-W4-LAND.sh` → gates → `git commit -S`
4. `git push` → CI verde → rc.2 → hold 24h → GA

---

## 5. Critérios de aceite

- [ ] **AC-1** `docs/ownership-decision-table.md` enumera as 9 dimensões,
      declara **toda** regra de poda com motivo, e não duplica valores do TSV.
- [ ] **AC-2** `ownership_table.tsv` é a fonte única, com as 14 colunas
      e `id` estável.
- [ ] **AC-3** `test-ownership-table.sh` roda toda linha contra os
      scripts REAIS (zero mock do sujeito), com timeout por célula.
- [ ] **AC-4** Mapa **100% verde** no clone do W2.
- [ ] **AC-5** Os 20 achados aplicados + os 4 abertos do round 11 estão
      no TSV com `origin` nomeando o round, todos verdes. **Enumeração
      literal, não contagem** — a fonte é
      `archive/codex-review-w1-round{2..11}.md`.
- [ ] **AC-6** `grep -n _ownership_verdict scripts/install.sh scripts/upgrade.sh`
      mostra chamada nos dois, e os ramos de decisão antigos saíram.
- [ ] **AC-7** e2e F3 45/45 · bateria sem failure · `shellcheck -S warning`
      limpo · `bash -n` OK.
- [ ] **AC-8** Rail do W3 encerrado por APPROVE, por 2 rodadas limpas, ou
      por teto — **com o motivo registrado**. Encerrar por silêncio é
      proibido ([[feedback-pair-rail-clean-round-not-proof]]).
- [ ] **AC-9** Gates do W4 verdes, incluindo o diff staged-vs-script.
- [ ] **AC-10** `ADR-190` registra a tabela como contrato e declara o
      `ADR-155-AMEND-1` **emendado** (não revogado).

---

## 6. Regras do run autônomo (anti-loop)

Estas regras existem porque a S296 as violou na prática.

1. **Nunca editar arquivo canônico na árvore viva.** Todo W2 é no clone.
   A árvore viva só muda no W5, pelas mãos do Owner.
2. **Nunca corrigir ramo a ramo.** Achado vira **linha de tabela**; a
   correção é na função única.
3. **Teto de 4 rodadas no W3.** Atingido, PARA e reporta.
4. **Toda claim do rail é verificada antes de virar código** — controle
   plantado, positivo E negativo. Foi o que segurou a qualidade na S296.
5. **Ao consertar um, varrer a família.** 4 achados da S296 foram irmãos
   atrasados (`install.sh` fazendo diferente do `upgrade.sh`).
6. **Espelhamento por tabela path→patch**, nunca lista manual — o
   `mirror-fixes.sh` da S296 cobria 2 de 4 arquivos e **nenhum gate
   acusou** (o `shasum -c` valida o staged contra si mesmo, não contra a
   árvore viva).
7. **Snippets em POSIX**, nunca `\s` em `grep`/`sed`.
8. **`git add` explícito, nunca `-A`** — a árvore tem canônicos sujos.
9. **Esperar por artefato, nunca por `pgrep -f`** (o waiter casa a si
   mesmo). Se o log diz que acabou, acabou — o log ganha do pgrep.
10. **Se o mapa não fechar em 100% ou o run travar**, o entregável passa
    a ser o **relatório** (tabela + mapa + o que falta), não um pack
    parcial. Pack parcial assinado é pior que nenhum pack.

---

## 7. Disposição do PLAN-166

- **Grupo A (trem de release)** — `npm-trusted-publisher.txt`,
  `pair-rail-verdict-template.md`, `test_release_workflow_asserts.py`,
  `npm-publish.yml`, `release.yml`, `RELEASE.md`: **zero achados em 11
  rodadas**. Permanece aplicado na árvore viva e entra no mesmo commit
  do W5. Não é objeto deste plano — **não mexer**.
- **Grupo B (F3)** — a lógica de decisão é **substituída** pelo produto
  do W2. Os fixes da S296 seguem na árvore como referência até o W5, e
  são sobrescritos pelas cópias staged no land.
- `ADR-155-AMEND-1` é **emendado** pelo `ADR-190`, não revogado: a
  intenção estava certa; a realização por ramos espalhados é que não.
- O sentinel atual do PLAN-166 (anchor `516e64e`) fica **obsoleto** — o
  W5 assina um novo cobrindo grupo A + os guardados do PLAN-167.
- Os **follow-ups nomeados** no `W1-ceremony-log.md` (transição
  maintainer→user no e2e; emits de GRANT do kernel; matcher do
  GUIA-COMPLETO; deferred-apply Route B) seguem válidos. O primeiro deles
  é **absorvido** por este plano: vira célula da tabela.

---

## 8. Riscos

| Risco | Mitigação |
|---|---|
| A tabela nasce incompleta e o loop volta em outra forma | O W3 revisa a TABELA; célula faltando é achado de primeira classe. Teto de 4 rodadas impede o renascimento. |
| O refactor quebra caminho hoje verde | Mapa-baseline do W0.4 é o controle: célula verde que fica vermelha para o W2 na hora. |
| Espaço grande demais para enumerar | Regra de poda do W0.1, com motivo declarado por regra. Poda silenciosa é proibida. |
| Observação do veredito ambígua (2 candidatos de hash iguais) | O harness diferencia os fixtures até desempatar; nunca resolve por preferência. |
| Run noturno não termina | Regra 10: relatório, não pack parcial. |
| Debate pede lib nova (path canônico novo) | Exigiria cerimônia de kernel. Preferência declarada pela lib existente; veto escala ao Owner de manhã. |

---

## 9. Registro de execução

<!-- o run autônomo anexa aqui: commit ativo, onda corrente, próxima ação concreta -->

- **Estado inicial (2026-08-06, S296):** HEAD `516e64e`, árvore suja com
  os 20 fixes do F3 (rounds 6-11) + grupo A aplicado, **4 achados do
  round 11 abertos e deliberadamente NÃO corrigidos** (viram linhas da
  tabela). 11 vereditos do codex em `.claude/plans/PLAN-166/archive/`.
  e2e 45/45, bateria 5011 passed / 0 failed, manifesto staged 34/34.
- **Próxima ação:** §0 checklist da primeira hora, item 1.

### Run autônomo — 2026-08-06/07 (S297)

> Bloco de retomada. Uma sessão nova lê SÓ isto para continuar.

**§0 (primeira hora): CONCLUÍDO.** HEAD confirmado `516e64e`, árvore suja
preservada (nada de `checkout --`), 11 vereditos + `W1-ceremony-log.md` +
`ADR-155`/`AMEND-1` lidos na íntegra.

**W0.1/W0.2/W0.3: CONCLUÍDOS.** Artefatos na superfície LIVRE, ainda
NÃO commitados:
- `docs/ownership-decision-table.md`
- `scripts/tests/ownership_table.tsv` (61 linhas, 14 colunas, ids estáveis)
- `scripts/tests/test-ownership-table.sh` (`bash -n` + `shellcheck -S warning` limpos)

**Correções de rota já aplicadas (não repetir):**
1. **3 das 5 regras de poda do §W0.1 deste plano são FALSAS** e foram
   rejeitadas com motivo no doc §4.1. A pior: `prior_record=link_* ⇒
   mode=link` teria apagado o achado ABERTO r11-F1 do espaço.
2. **AC-5: são 35 achados literais, não 24.** A contagem de memória estava
   errada. Ledger completo no doc §8 (29 células + 2 invariantes + 4
   não-células nomeadas).
3. **1º mapa-baseline (40 RED) era instrumento quebrado, não código.**
   ~16 vermelhos vinham de o harness desempatar `hash_source` por
   PREFERÊNCIA DE ORDEM. Causa-raiz: o fixture usava a MESMA fonte para o
   install-base e para o upgrade, tornando `HASH_SOURCE` e
   `HASH_PRIOR_RECORD` iguais por construção. Curado DIFERENCIANDO o
   fixture (fonte `src-next` perturbada), nunca relaxando o critério.

**Achados NOVOS da tabela (viram linha, NÃO patch de ramo):**
- `_refresh_protocol_pointer` não tem guard de destino não-regular nem de
  symlink-leaf (doc §5.1). R-11 mostrou que o guard de ancestral seria
  vacuoso ali — não remendar.
- **§5.7 (o mais sério):** o FIFO NÃO trava na rota do marker; trava em
  `check-model-deprecations.py`, scanner que varre a árvore ANTES de
  qualquer refresh. Provado isolado com controle positivo E negativo.
  Efeito colateral pior: os guards r2-F3/r9-F3 estão MASCARADOS — nenhum
  e2e os alcança, então uma suíte verde não prova nada sobre eles.

**Onda corrente:** W0.4 — mapa-baseline **v3** rodando (~25 min).

**Três defeitos de FIXTURE achados em três triagens sucessivas** (o
instrumento precisou de tanto escrutínio quanto o sujeito):

| # | Defeito | Sintoma | Cura |
|---|---|---|---|
| 1 | fonte única p/ install-base e upgrade | `HASH_SOURCE` ≡ `HASH_PRIOR_RECORD`; harness desempatava por PREFERÊNCIA | fonte `src-next` perturbada |
| 2 | `install_fresh` extraía um base | rerun disfarçado de fresh; violava a R-01 | alvo estruturalmente vazio |
| 3 | symlink repontado em TODA linha | linhas `link_match` testavam `link_retargeted` | não tocar o symlink quando `prior_record=link_match` |

**O #3 é o mais instrutivo: no mapa v1 aquelas linhas estavam VERDES.**
Verde falso — passavam pelo motivo errado. Confiar no v1 teria "provado"
preservação de LINK usando um link redirecionado.

**Achado novo #4 (doc §5.8):** a linha de continuidade dentro do guard de
ancestral-symlink é **código morto**. O sanitizador de relpath descarta
qualquer registro cujo caminho atravesse symlink no LOAD, antes de
`_baseline_has_*_record` ser consultado. Cura NÃO é fazê-la disparar
(isso violaria a fence de proveniência da decisão (v) do ADR-155) — é
**apagar a linha**: promessa que não se cumpre é pior que ausência.

### ESTADO EM 2026-08-07 ~00:35 — W0 e W1 FECHADOS, W2 EM CURSO

**Commits locais (não pushados):** `a09427f` W0 · `4fd4ba2` W1 round 1 ·
`+1` C1 do consenso. Baseline gravado: **50 verde / 11 vermelho**, todos os
11 atribuídos a defeito real.

**W1 fechado — 3 ADJUST, 0 VETO, `design-coherent`.** Consenso em
`PLAN-167/debate/round-1/consensus.md`. Decisões que já aterrissaram:
- **C1** — `fault` virou a 10ª dimensão (TSV a 15 colunas);
  `legacy_pristine_partial` virou valor de `live_content`. `note` agora é
  prosa apenas. OQ-7 RESOLVIDA.
- **C2** — split decisão/execução adotado, cláusula `inherits their
  hash_source` RISCADA e substituída pela **INV-3** (falha de execução
  nunca avança o registro). Consequência aplicada: recusar-se a agir sobre
  arquivo especial é DECISÃO, não falha — o regex de abort foi estreitado.
- **OQ-9 reconciliada** a uma regra única: `OMIT_RECORD` e
  `PRESERVE_UNOWNED` diferem só por `prior_record`, que já é coluna.
- **Achado promovido:** o harness era CEGO a escrita fora da árvore.
  Tripwire armada (status `ESCAPE`). `OWN-0034` reporta ESCAPE — o `cat >`
  do ponteiro escreve FORA do alvo. É classe S238 PROVADA, não hipótese.

**W2 em curso — clone overlay:** caminho em `scratchpad/CLONE_PATH`
(paridade verificada: 29 arquivos modificados no clone e na árvore viva).
- ✅ `_ownership_verdict()` implementada em `scripts/_framework_manifest_set.sh`
- ✅ `scripts/tests/test-ownership-verdict-unit.sh` instalado
- ✅ **Oráculo unitário: 59 PASS / 0 FAIL / 2 excluídos contados**
  (`OWN-0024`/`OWN-0027` são células de EXECUÇÃO, cobertas pelo e2e)

**W2.2 EM CURSO — método: MODO SOMBRA antes da troca.**

O oráculo unitário prova que a função combina com a TABELA. O e2e prova que
os callers combinam com a tabela. Nada provava que a função combina com o
que os callers OBSERVAM — e é essa a lacuna que a troca direta assumiria
sem medir. Então: observadores instalados no clone (`_ov_obs_*`), a função
é chamada, o resultado é REGISTRADO e **não age** (`OV-SHADOW` no log).

Isso converte o risco restante em dados: cada divergência é ou a função
errada ou a cascata errada — a pergunta que a tabela existe para tornar
respondível. E **linha sem registro de sombra NÃO é aprovação**: significa
que o caller retornou antes do ponto de observação, ou seja, a função nunca
foi consultada. Mesma classe do mascaramento do §5.7.

Artefatos prontos no scratchpad (aplicar quando a sombra fechar):
- `spec_observers.sh` — já instalado no clone
- `refresh_spec_refactored.sh` — o `_refresh_spec_contract` novo
  (observe → decide → execute), com a INV-3 no caminho de backup falho
- `analyse_shadow.py` — a análise de divergência

**Erro de método corrigido:** rodei duas suítes e2e concorrentes (viva +
clone), o que dobrou a contenção e fez as duas rastejarem. Serializar.

**Erro de medição corrigido:** eu lia o progresso do scratch mais recente
por mtime, que era um dos preservados com `--keep` nos diagnósticos. Derive
o scratch do CABEÇALHO do próprio arquivo de saída da corrida.

**DEPOIS:** W2.3 (remover `FMS_HASH_ROOT_PATHS`/`FMS_LINK_PATHS` —
substituir, não somar), W2.4 (e2e a 100%), W2.5 (gates), W3, W4.

**Dívidas de infra registradas nesta noite (não bloqueiam):**
`inject-agent-context.sh` falha a busca de persona mesmo com nome exato do
`team.md`, e não emite `FILE ASSIGNMENT` que o hook exige — prompts foram
montados à mão. Achados de CI do devops (path filters ausentes,
`fetch-depth:1` sem tags) vão para o pack do W4: workflows são canônicos.

**Gates já verificados adiantado:** docs-freshness bloqueante = 610
arquivos / 0 refs quebradas / EXIT=0. shellcheck do CI cobre só
`.claude/{scripts,hooks}` — o harness fica fora do gate (rodado limpo
localmente mesmo assim).

**Owner confirmou (2026-08-06, noite):** assina de manhã o que for
necessário. Logo o W4 entrega pack STAGED e INASSINÁVEL
(`Anchor-SHA: <PLACEHOLDER>`); o run NÃO tenta assinar nada.

**⚠️ Correção obrigatória ao §W2 deste plano (descoberta S297).** O §W2
manda `git clone --local .`, que clona o **HEAD** — e os 20 fixes do F3 da
S296 estão SÓ na árvore suja, nunca commitados. O clone nasceria de um
baseline DIFERENTE do que o mapa do W0.4 mediu, e "dirigir o mapa a 100%"
(W2.4) mediria contra outro ponto de partida. Sequência correta:

```
git clone --local . "$CLONE"
git diff HEAD > "$SCRATCH/live-tree.diff"    # tracked, staged E unstaged
git -C "$CLONE" apply "$SCRATCH/live-tree.diff"
```

Conferir depois: `git -C "$CLONE" status --porcelain` deve espelhar o
`git status --porcelain` da árvore viva nos arquivos do grupo A + F3.
Sem isso o W2 otimiza contra o alvo errado.

**Desvio de nomenclatura:** o §W1 deste plano pede
`debate/round-{1,2,3}/consensus.md`, mas o `DEBATE-SCHEMA.md` §3 marca
`debate/` como LEGADO e `architect/` como prática atual (foi o que o
PLAN-166 usou). Vale `architect/`.

**Desenho do W2 (levar ao debate como proposta concreta).**
`_ownership_verdict()` é uma **função PURA das 9 dimensões**:

```
_ownership_verdict <surface> <prior_record> <live_type> <live_content> \
                   <source_has> <mode> <ceremony> <operation> <skip_requested>
# stdout: "<VERDICT> <HASH_SOURCE>"   (o par do doc §3)
```

Consequência que muda a economia da suíte: o mesmo TSV vira **dois**
oráculos —
1. **unitário**, chamando a função direto (milissegundos, 61 linhas, roda
   a cada edição);
2. **e2e**, o `test-ownership-table.sh` atual (~10 min, prova que os
   callers OBSERVAM as dimensões corretamente e EXECUTAM o veredito).

Os dois são necessários e testam coisas diferentes: o unitário pega
decisão errada, o e2e pega observação errada. O loop de 40 min da S296
existia porque só havia o caro — e ele nem cobria as células.

Os callers (`install.sh`/`upgrade.sh`) ficam com: observar as 9 dimensões
→ chamar → executar. Os ramos de decisão antigos SAEM (AC-6).
