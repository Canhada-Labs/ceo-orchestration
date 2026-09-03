# PLAN-186 W0-US5 — Censo mecânico das 4 (+1 candidata) superfícies de roteamento papel→modelo

> Escopo: AC-12 do PLAN-186 (`.claude/plans/PLAN-186-orchestrator-operating-model.md:181`) e a
> descrição de US5 (`:127-128`, dentro de W0). Leitura mecânica, sem redefinir a pergunta.
> Repo em `main` @ `400638e`, árvore limpa no lançamento. READ-ONLY — nenhum arquivo do repo
> foi tocado; só este relatório foi escrito.

## 0. Achado prévio (não estava no escopo nomeado, mas é material)

Existem **DUAS constantes chamadas `VETO_HARDCODE`**, em módulos diferentes, com **semânticas
diferentes** — mesma grafia, fatos distintos:

- `.claude/scripts/tier_policy_cli/_constants.py:44-47` → `role -> model id` (`Dict[str, str]`),
  2 papéis: `code-reviewer`, `security-engineer` → `"claude-fable-5"`. **Esta é a superfície #4
  do enunciado** (a que `set-quality-profile.sh` deriva).
- `.claude/hooks/_lib/tier_policy/_constants.py:196-217` → `role -> frozenset(task_types)`
  (ex.: `code-reviewer` → `{"complexity-review", "diff-review", ...}`), NÃO carrega model id
  nenhum. É uma tabela de ELEGIBILIDADE de tipo de tarefa para o piso VETO, não de roteamento
  de modelo.

Um leitor apressado que grepasse só `VETO_HARDCODE` sem checar o módulo de origem citaria o
fato errado. Tratado abaixo como duas linhas distintas da tabela (4a e 4b).

## 1. Tabela role/arquétipo × superfície

| papel/arquétipo | (1) `agents/*.md` pin | (2) `MODEL_HINT` (inject-agent-context.sh) | (3) `routing-matrix.yaml` `coder_model` | (4a) `tier_policy_cli.VETO_HARDCODE` (scripts) | concordam? |
|---|---|---|---|---|---|
| code-reviewer | `claude-fable-5` (`agents/code-reviewer.md:6`) | hint=`opus` (skill `code-review-checklist`, `:280-283`) | `opus` (`routing-matrix.yaml:53,55`) | `claude-fable-5` (`tier_policy_cli/_constants.py:45`) | **NÃO** — (1)/(4a) citam um id de modelo (`claude-fable-5`), (2)/(3) citam só um ALIAS de família (`opus`); `claude-fable-5` não é um alias "opus", é sua própria família. Compatível só se "opus" for lido como "camada VETO", não como família literal. |
| security-engineer | `claude-fable-5` (`agents/security-engineer.md:6`) | hint=`opus` (skill `security-and-auth`, `:280-283`) | `opus` (`routing-matrix.yaml:83,85`) | `claude-fable-5` (`tier_policy_cli/_constants.py:46`) | **NÃO** — mesmo padrão do code-reviewer. |
| identity-trust-architect | `claude-fable-5` (`agents/identity-trust-architect.md:6`) | sem branch dedicado — cai no fallback `*)`→`sonnet` (`:310-313`) SE o skill detectado não bater nos branches VETO/financeiro | ausente da yaml (arquétipo não listado) | ausente | **NÃO-COMPARÁVEL** — (1) pina fable-5 (piso VETO por convenção do time, não por `VETO_HARDCODE`, que só nomeia 2 papéis); (2)/(3) não têm entrada dedicada para este arquétipo. |
| incident-commander | `claude-fable-5` (`agents/incident-commander.md:6`) | sem branch dedicado (fallback `*)`→`sonnet`, salvo detecção de skill financeiro/VETO) | ausente da yaml | ausente | **NÃO-COMPARÁVEL**, mesmo padrão. |
| threat-detection-engineer | `claude-fable-5` (`agents/threat-detection-engineer.md:6`) | skill primária `security-and-auth` (`team.md:209`) → hint=`opus` (`:280-283`) | `opus` (`routing-matrix.yaml:213,215`) | ausente | **NÃO** em formato (id exato × alias × alias); em TIER concordam — todos ≥ piso VETO. |
| devops | `claude-sonnet-4-6` (`agents/devops.md:6`) | skill `devops-ci-cd` → hint=`sonnet`, razão "security-adjacent... haiku risky" (`:300-303`) | ausente da yaml | ausente | **SIM** entre (1) e (2) — ambos "sonnet"; (3)/(4a) não opinam. |
| llm-finops-architect | `claude-sonnet-4-6` (`agents/llm-finops-architect.md:6`) | skill primária `llm-routing-and-finops` (`team.md:210`) — AUSENTE do case → fallback `*)` → hint=`sonnet` (`:310-313`) | ausente da yaml | ausente | **SIM** entre (1) e (2) em tier (sonnet), mas por FALLBACK, não por decisão explícita — a concordância é acidental. |
| performance-engineer | `claude-sonnet-4-6` (`agents/performance-engineer.md:6`) | skill `performance-engineering` → hint=`sonnet` (`:295-298`) | `sonnet` (`routing-matrix.yaml:132,134`) | ausente | **SIM** — (1)/(2)/(3) concordam em "sonnet". |
| qa-architect | `claude-sonnet-4-6` (`agents/qa-architect.md:6`) | skill `testing-strategy` → hint=`sonnet` (`:295-298`) | `sonnet` (`routing-matrix.yaml:107,109`) | ausente | **SIM** — (1)/(2)/(3) concordam. |

Observação de forma: (2) e (3) nunca emitem um **model id completo** — (2) emite só o alias
`opus`/`sonnet` (nem chega a existir um `haiku` no case block hoje, apesar do comentário de
`devops-ci-cd` mencionar haiku como contraste), (3) emite a palavra `opus`/`sonnet` como
`coder_model` (não `claude-opus-5` etc.). Só (1) e (4a) carregam o id completo
(`claude-fable-5`, `claude-sonnet-4-6`). Isso por si só é uma classe de discordância: nenhuma
das 4 superfícies fala a mesma "linguagem" (id completo vs. alias vs. papel implícito).

`routing-matrix.yaml` cobre 8 arquétipos nomeados (`code-reviewer`, `security-engineer`,
`qa-architect`, `performance-engineer`, `refactoring`, `docs-writer`, `test-author`,
`threat-detection-engineer` — linhas 53, 83, 107, 132, 155, 172, 189, 213). Dos 13 arquivos em
`agents/`, 9 têm `model:` e 4 são probes/dispatch sem `model:`. **União dos papéis** (errata do
rail S340): a interseção agentes × matriz é de **5** (`code-reviewer`, `security-engineer`,
`qa-architect`, `performance-engineer`, `threat-detection-engineer`); **8** arquivos são
só-agentes (`devops`, `identity-trust-architect`, `incident-commander`, `llm-finops-architect`
+ os 4 `_probe_*`/`_dispatch`); **3** papéis são só-matriz (`refactoring`, `docs-writer`,
`test-author`, todos `coder_model: sonnet`) e NÃO têm `agents/*.md`. Uma tabela fonte-única tem
de carregar a UNIÃO (12 papéis; os 4 probes ficam fora por não rotearem), senão a matriz perde
rotas ou mantém fato local. **E o `MODEL_HINT` (2) não roteia por PAPEL dos 12** (errata do
rail S340 r2): `inject-agent-context.sh:217-246` resolve QUALQUER persona dos mapas
team/frontend/domínio para a skill primária e daí para o alias — ex.: `VP Engineering` →
`architecture-decisions` → `opus`, sem linha entre os 12. Uma tabela por papel não o cobre; a
W-ROTA precisa de uma segunda relação skill→tier (ou persona→skill→tier) como fonte do case
block, senão (2) continua dona local.

## 2. Classificação por superfície

### (1) `.claude/agents/*.md` — pins de frontmatter
- Fato: `model: <id>` na linha 6 de cada um dos 9 arquivos com o campo (9/13; os 4 sem campo
  são `_dispatch.md`, `_probe_architect.md`, `_probe_canonical_edit.md`,
  `_probe_missing_skill.md` — herdam `inherit`).
- Fable-5 (piso VETO por convenção): `code-reviewer.md:6`, `identity-trust-architect.md:6`,
  `incident-commander.md:6`, `security-engineer.md:6`, `threat-detection-engineer.md:6`.
- Sonnet-4-6: `devops.md:6`, `llm-finops-architect.md:6`, `performance-engineer.md:6`,
  `qa-architect.md:6`.
- Leitores: `.claude/hooks/_lib/agent_frontmatter.py` (parser canônico do campo),
  `.claude/hooks/_lib/tier_policy/_constants.py` + `_agent_frontmatter.py` (União com
  `VETO_FLOOR_ROLES`), `.claude/scripts/set-quality-profile.sh` (reescreve estes mesmos
  arquivos por perfil — awk+mv, ver §0 do script).
- **ERRATA do rail r11 (P2): `escalation_signals.py` NÃO é leitor dos pins — é dona local
  (6).** Ele nunca parseia `.claude/agents/`; `.claude/hooks/_lib/escalation_signals.py:61-71`
  hardcoda `_VETO_ROLES = {code-reviewer, security-engineer}` (**2 dos 5** papéis VETO — o
  próprio comentário `:64-69` declara a lacuna como «acknowledged drift», decisão separada do
  Owner) e `_FLOOR_TIER_PREFIXES = (claude-opus-, claude-fable-)`. É uma política independente,
  com universo de papéis MENOR que o de `VETO_FLOOR_ROLES`, e a divergência é a mesma forma
  D1-D4: dois donos do fato «quem é VETO» que não se falam. Entra no censo como dona local
  (6) — política de escalação hardcodada — e a W-ROTA a lista como leitora a converter.
- Classificação: **DONA LOCAL**. É o que o harness lê no spawn **NATIVO** (`subagent_type` /
  `agentType` = arquétipo) sem `model:` explícito — medido na US4 desta noite (`code-reviewer`
  → `claude-fable-5`, `qa-architect` → `claude-sonnet-4-6`). No rail **MITIGADO**
  (`general-purpose` + persona injetada) o pin fica DORMENTE e vale a herança do assento
  (`inject-agent-context.sh:738-782`; US4 linha 2). Não deriva de nenhuma tabela upstream; é
  editado por cerimônia (`check_canonical_edit.py`) e por `set-quality-profile.sh`.

### (2) `MODEL_HINT` case block — `.claude/scripts/inject-agent-context.sh:278-314`
- Fato completo do `case "$DETECTED_SKILL" in` (`:278`) ao `esac` (`:314`):
  - `code-review-checklist|security-and-auth` (`:280`) → `MODEL_HINT="opus"` (`:281`),
    razão "VETO floor (ADR-052) — Opus mandatory" (`:282`).
  - `architecture-decisions|pre-plan-brainstorm|agent-architect|ai-llm-orchestration` (`:285`)
    → `opus` (`:286`), razão "reasoning L3+ multi-step / debate Round N" (`:287`).
  - `financial-correctness-and-math|monetization-and-billing|compliance-lgpd|consent-lifecycle|dpo-reporting|pii-data-flow|state-machines-and-invariants|data-schema-design`
    (`:290`) → `opus` (`:291`), razão "VETO-eligible domain (financial / legal /
    correctness)" (`:292`).
  - `testing-strategy|performance-engineering|public-api-design|chaos-and-resilience|incremental-refactoring|observability-and-ops|product-conversion-readiness|growth-and-launch`
    (`:295`) → `sonnet` (`:296`), razão "mechanical work / measurement / API enumeration; CEO
    Opus reviews report" (`:297`).
  - `devops-ci-cd` (`:300`) → `sonnet` (`:301`), razão "CI/CD is security-adjacent (SHA-pin,
    OIDC, secrets); haiku risky without tournament evidence" (`:302`).
  - `terse-mode` (`:305`) → `sonnet` (`:306`), razão "output economy / listings" (`:307`).
  - fallback `*)` (`:310`) → `sonnet` (`:311`), razão "default for unknown archetype
    (mechanical fallback); upgrade to opus if reasoning-heavy" (`:312`).
- O comentário logo acima do `case` (`:269-277`) é ele mesmo a declaração normativa do que este
  bloco É: "This block emits a **recommended** model based on detected skill so the CEO can
  copy/paste" (`:276-277`) — não é lido por nenhum outro script; é saída de texto para humano.
- O valor emitido é um **alias** (`opus`/`sonnet`), nunca um model id completo — confirmado:
  não há `claude-` em nenhuma linha do case block.
- Leitores: nenhum consumidor programático fora do próprio script achado por grep — só os
  documentos de plano/debate do PLAN-186 e PLAN-169 (que CITAM o bloco em prosa, não o
  invocam).
- Classificação: **DONA LOCAL, mas de baixa força** — é a única das 4 que não é lida por
  nenhuma outra máquina; é uma recomendação textual para o operador humano copiar/colar no
  parâmetro `model` do `Agent()`/`Task()`. Não há enforcement: se o CEO ignorar o hint, nada
  bloqueia.

### (3) `.claude/dispatcher/routing-matrix.yaml`
- Fato: chave `coder_model` por arquétipo, 8 entradas — `code-reviewer:55`=`opus`,
  `security-engineer:85`=`opus`, `qa-architect:109`=`sonnet`, `performance-engineer:134`=`sonnet`,
  `refactoring:157`=`sonnet`, `docs-writer:174`=`sonnet`, `test-author:191`=`sonnet`,
  `threat-detection-engineer:215`=`opus`.
- O cabeçalho do arquivo (`:1-33`) já documenta a semântica: `coder_model` é "model floor for
  the coder (per ADR-052 / ADR-064)" (`:6`), e a nota normativa (`:28`) diz "VETO-floor
  archetypes (CR + Sec + IDX + IC + TDE) coder=claude, model=opus per ADR-052" — mas **IDX e
  IC (identity-trust-architect, incident-commander) NÃO TÊM entrada na yaml**, apesar de
  citados no comentário como membros do piso. Isso é uma discordância DOCUMENTO-vs-DADO dentro
  da própria superfície (3): o comentário promete 5 papéis, o `archetypes:` map cobre 3
  deles com `opus` (`code-reviewer:55`, `security-engineer:85`, `threat-detection-engineer:215`)
  e omite IDX e IC.
- Schema versionado (`schema_version: "1.0.0-rc.1"`, `:31`), validado por
  `.claude/dispatcher/routing-matrix-loader.py` no load; SHA-pinned na carga (comentário
  `:36-38`).
- Leitores REAIS (árvore viva; **errata do rail r12, P2 — a lista anterior era um grep por
  NOME do arquivo, não por LEITURA do conteúdo**, e por isso incluía quem só guarda o path
  (`check_canonical_edit.py`), quem serializa campos já dados (`audit_emit.py`), quem checa
  existência (`validate-governance.sh`) e quem recebe o mapa já parseado
  (`disable_predicate_eval.py`) — nenhum deles LÊ a matriz): `.claude/dispatcher/routing-matrix-loader.py`
  (o único parser; SHA-pin na carga) e, via o loader, `.claude/hooks/check_pair_rail.py`,
  `.claude/scripts/inject-agent-context.sh` (`--pair-mode`) e `.claude/scripts/run-promotion-gate.py`.
  A regra que fica para a W-ROTA: consumidor é quem chama o LOADER, derivado do grafo de
  import/chamada — nunca de `grep -l routing-matrix`.
- Classificação: **DONA LOCAL** — é a fonte de verdade do par coder/reviewer do pair-rail
  (PLAN-081), com enforcement real via `routing-matrix-loader.py` + SHA-pin; não deriva de
  nenhuma tabela upstream hoje.

### (4a) `tier_policy_cli._constants.VETO_HARDCODE` (+ (4b) o par de mesmo nome em `hooks/_lib`)
- Fato (4a): `.claude/scripts/tier_policy_cli/_constants.py:44-47` — `{"code-reviewer":
  "claude-fable-5", "security-engineer": "claude-fable-5"}`. SHA256 canônico calculado na
  linha `:67` (`VETO_HARDCODE_FROZEN_SHA256`); espelho INDEPENDENTE (não importado) em
  `.claude/scripts/tier_policy_cli/apply.py:90-93` (`VETO_HARDCODE_APPLY`, mesmos 2 papéis/id),
  com o hex literal `FROZEN_SHA256_HEX_LITERAL` colado logo abaixo (`apply.py:95-100`,
  valor `0419e4fc...`) — defesa-em-profundidade: os dois literais têm que bater
  byte-a-byte via `_compute_canonical_sha256`.
- `set-quality-profile.sh` (`.claude/scripts/set-quality-profile.sh:75-121`, função
  `_veto_floor_model`) deriva o modelo do piso VETO **lendo `apply.py` como TEXTO** (não
  `import`, porque puxa `_lib.runtime_paths` que não existe no sandbox de teste — comentário
  `:62-64`) para achar o hex de 64 chars na janela de 800 chars após o token
  `FROZEN_SHA256_HEX_LITERAL` (`:97-99`), comparando com o SHA recomputado de
  `tier_policy_cli._constants.VETO_HARDCODE` (`:100-104`) — falha FECHADA (exit 3/4/5/6) se
  qualquer uma das duas leituras não bater ou o papel não existir (`:105-112`).
- Leitores de (4a) na árvore viva: `.claude/scripts/tier_policy_cli/learn.py` (zeroth-check
  `:810-812` — papéis em `VETO_HARDCODE` nunca são recomendados para demote),
  `.claude/scripts/set-quality-profile.sh` (acima), suíte própria (`tests/test_constants.py`,
  `tests/test_learn_mutation.py`, `tests/test_apply.py`, `tests/test_task_route.py`).
- (4b) `.claude/hooks/_lib/tier_policy/_constants.py:196-217` — mesmo nome de símbolo, tipo de
  valor diferente (`role -> FrozenSet[task_type]`, não `role -> model_id`); consumido por
  `.claude/hooks/check_tier_policy.py` e a suíte `.claude/hooks/tests/test_tier_policy_*.py`.
  **ERRATA do rail r6 (P2-c): `task-route.py` é leitor de (4b), NÃO de (4a)** — a versão
  anterior deste relatório o listava entre os leitores de (4a) e isso é FALSO em disco:
  `.claude/scripts/task-route.py:70` importa `from _lib.tier_policy._constants import
  VETO_HARDCODE`, que é o mapa `role -> FrozenSet[task_type]`, e não o
  `tier_policy_cli._constants.VETO_HARDCODE` (`role -> model_id`). Os dois símbolos têm o
  MESMO nome e semânticas diferentes; migrar (4a) na W-ROTA não alcança `task-route.py`, e
  tratá-lo como leitor de (4a) faria a wave declarar cobertura que não tem. A homonímia é,
  por si, um achado do censo: é a forma exata do defeito que a rota única existe para fechar.
  **Não pertence à pergunta fixada** (não é role→modelo) — citado aqui só para que a wave
  W-ROTA não confunda os dois símbolos homônimos ao desenhar a tabela fonte-única.
- Classificação: **DONA LOCAL** (4a) — único par com defesa-em-profundidade de 2 literais +
  SHA congelado, e o único consumido por um script que RECUSA rodar se a autoridade estiver
  ilegível ou adulterada (fail-closed, citado no próprio `set-quality-profile.sh:113-121`
  como "PLAN-169 W4.3 F1"). (4b) é **FORA DE ESCOPO** — mesma grafia, fato diferente.

## 3. Candidata 5ª superfície — ADR-149 (`AVAILABLE_MODELS_WORKING_SET` / `VETO_FLOOR_ALLOWED`)

- `VETO_FLOOR_ALLOWED: frozenset` — `.claude/adr/ADR-149-model-id-allowlist.md:33-37`:
  `{"claude-opus-4-8", "claude-fable-5", "claude-opus-5"}`. Comentário normativo na Amendment 1
  (`:115`): "VETO eligibility is exclusively `VETO_FLOOR_ALLOWED` membership".
- `AVAILABLE_MODELS_WORKING_SET: tuple` — `:80-96`: 7 ids em ordem normativa (`claude-opus-4-8`,
  `claude-fable-5`, `claude-sonnet-4-6`, `claude-haiku-4-5`, `claude-opus-5`,
  `claude-sonnet-5`, `claude-fable-5-1` — o último por Amendment 2, `:240-244`,
  "APPENDED AT END").
- `FALLBACK_MODEL_CHAIN: tuple` — `:100-102`: `("claude-opus-5",)`.
- Consumidor: `.claude/scripts/generate-available-models.py` — `--check` compara SÓ
  `availableModels` e `fallbackModel` dos settings resolvidos com `AVAILABLE_MODELS_WORKING_SET`
  / `FALLBACK_MODEL_CHAIN` (`run_check`); após o Amendment, o parser retorna assim que lê o
  working set (`:106-108`) e `VETO_FLOOR_TOKEN` é só fallback pré-emenda (`:109-119`). **Não
  valida `VETO_FLOOR_ALLOWED`** — essa paridade é coberta por OUTRO oráculo:
  `.claude/hooks/tests/test_adr149_validator_parity.py:167-177` asserta igualdade de CONJUNTO
  entre o bloco do ADR e `_lib.agent_frontmatter.VETO_FLOOR_ALLOWED` (errata do rail S340 r3: a
  versão anterior deste censo dizia que nenhum check o fazia).
- **Veredito: NÃO decide papel→modelo — decide FLEET MEMBERSHIP.** Nenhum dos dois blocos tem
  chave por papel/arquétipo; são conjuntos/tuplas planas de ids permitidos (disponibilidade de
  seleção em qualquer superfície do harness) e elegibilidade de VETO (que id PODE servir um
  veredito VETO), respectivamente. É a autoridade que as outras 4 superfícies (1)-(4a)
  PRESSUPÕEM (todo id que elas citam tem que estar em `AVAILABLE_MODELS_WORKING_SET`, e todo id
  usado num papel VETO tem que estar em `VETO_FLOOR_ALLOWED`), mas não escolhe QUAL id um dado
  papel recebe. Classificação: **LEITORA candidata seria o inverso do papel real** — na
  verdade ela é a AUTORIDADE de que as outras 4 são leitoras implícitas hoje (sem
  enforcement mecânico cruzado, exceto via `generate-available-models.py --check` sobre
  `settings.json`, que não toca nenhuma das 4).

## 4. LEITORA candidata vs. DONA LOCAL — resumo

| # | superfície | classe | por quê |
|---|---|---|---|
| 1 | `.claude/agents/*.md` pins | dona local | lido no spawn NATIVO (arquétipo como `subagent_type`/`agentType`) sem `model:` — US4; no rail mitigado o pin é dormente e vale a herança do assento; editado por cerimônia + `set-quality-profile.sh` |
| 2 | `MODEL_HINT` (`inject-agent-context.sh`) | dona local (fraca) | só recomendação textual; zero consumidor programático; emite ALIAS, não id |
| 3 | `routing-matrix.yaml` `coder_model` | dona local | fonte do par coder/reviewer do pair-rail, SHA-pinned no load, 8/13 arquétipos cobertos |
| 4a | `tier_policy_cli.VETO_HARDCODE` | dona local | defesa-em-profundidade dupla + fail-closed em `set-quality-profile.sh`; só 2/5 papéis VETO |
| 5 (cand.) | ADR-149 (`AVAILABLE_MODELS_WORKING_SET`/`VETO_FLOOR_ALLOWED`) | autoridade de fleet, não role→model | conjunto plano de ids, sem chave por papel — as 4 acima deveriam ser leitoras DELA para "este id existe?", nunca o inverso |

Nenhuma das 4 superfícies de role→modelo é hoje uma LEITORA de nenhuma tabela única — cada uma
guarda o fato duplicado, em formatos diferentes (id completo × alias × ausência de entrada), o
que é exatamente a forma do defeito D1-D4 que motivou a wave W-ROTA (`scripts/delivery-routes.tsv`).

**Errata (rail S340 r3, codex P1): este censo está INCOMPLETO.** Há pelo menos três donos VIVOS
a mais do fato papel→modelo, fora das 4 superfícies acima: `.claude/scripts/set-quality-profile.sh:157-169`
(hardcoda pares papel/modelo por perfil — ex.: `max-quality` dá `claude-opus-4-8` a QA, perf e
devops — e os ESCREVE nos `agents/*.md`), `.claude/scripts/task-route.py:504-555` (emite escolhas
papel/modelo próprias, `claude-opus-4-8`), e o fallback papel→modelo do audit log citado pelo
rail (`audit_log.py (a localizar):902-954`). E um quarto (rail r4): o baseline ADR-052 do tier-policy —
`tier_policy_cli/_types.py:202-237` (literais papel→modelo) que `tier_policy_cli/loader.py:111-113,423-460`
usa ATIVAMENTE quando `.claude/tier-policy.json` falta ou é inválido; já diverge do pin (`devops` =
Haiku lá, `claude-sonnet-4-6` em `agents/`). Uma W-ROTA limitada às 4 deixaria estes donos
divergentes e capazes de sobrescrever ou reportar rotas velhas — e o conjunto de donos tem de ser
DERIVADO (grep mecânico de literais de model id/alias por papel), não lembrado. **AC-12 fica ◐ até o censo os incluir** (o teste da
união de 12 papéis também é parcial: `task-route.py` roteia por papel próprio).

## 5. PROPOSTA — forma da tabela fonte-única W-ROTA (molde `delivery-routes.tsv`)

`scripts/delivery-routes.tsv` usa: comentário de proveniência no cabeçalho (linhas 1-11, cada
fato com `file:line` do measurement original) + colunas TSV
`dest_relpath \t source_relpath \t transform \t flag_dep`. O molde para role→modelo replicaria
essa forma:

```
# role-model-routes.tsv — tabela fonte-única role→modelo. THIS FILE IS THE TRUTH.
# TODO dono do censo (1)-(6) — os 4 originais + os 6 achados pelos rails r6-r12 — vira
# LEITORA desta tabela; nenhum re-deriva o fato. Chave COMPOSTA role × task_context
# (rail r9: task-route.py:534-542 roteia devops→Opus só em release|ci; `*` = qualquer).
# Medido em .claude/plans/PLAN-186/w0/us5-routing-surfaces-census-S340.md (S340/S341).
role	task_context	model_id	matrix_floor	veto_role	reason	adr_ref
code-reviewer	*	claude-fable-5	opus	true	VETO floor ADR-052	ADR-149
security-engineer	*	claude-fable-5	opus	true	VETO floor ADR-052	ADR-149
devops	*	claude-sonnet-4-6	sonnet	false	pin agents/devops.md	ADR-064
devops	release|ci	claude-opus-4-8	opus	false	task-route.py:534-542 (id DEFASADO — migrar no LAND)	ADR-064
identity-trust-architect	*	claude-fable-5	opus	true	VETO floor (convenção agents/*.md; ausente de VETO_HARDCODE/routing-matrix)	ADR-052
incident-commander	*	claude-fable-5	opus	true	idem	ADR-052
threat-detection-engineer	*	claude-fable-5	opus	true	VETO floor (routing-matrix.yaml:213)	ADR-052
llm-finops-architect	*	claude-sonnet-4-6	sonnet	false	advisory, sem VETO (ADR-052 amendment)	ADR-064
performance-engineer	*	claude-sonnet-4-6	sonnet	false	mecânico/medição	ADR-064
qa-architect	*	claude-sonnet-4-6	sonnet	false	mecânico/medição	ADR-064
refactoring	*	-	sonnet	false	só-matriz (sem agents/*.md); routing-matrix.yaml:155	ADR-064
docs-writer	*	-	sonnet	false	só-matriz; routing-matrix.yaml:172	ADR-064
test-author	*	-	sonnet	false	só-matriz; routing-matrix.yaml:189	ADR-064
```

**Errata do rail r6 (P2-b): o keyspace NÃO são os 12 papéis locais.** A união
`agents/*.md` ∪ `routing-matrix.yaml` dá 12, mas `_ADR_052_ROLE_TO_MODEL`
(`.claude/hooks/audit_log.py:922-954`, fallback quando `tool_response.model` é nulo) tem
**20 chaves** — derivadas mecanicamente: `code-reviewer`, `security-engineer`,
`qa-architect`, `performance-engineer`, `devops`, `general-purpose`, `growth-engineer`,
`billing-engineer`, `compliance-specialist`, `chaos-engineer`, `data-engineer`,
`real-time-systems-engineer`, `refactoring-lead`, `vp-engineering`, `vp-product`,
`vp-operations`, `incident-commander`, `identity-trust-architect`,
`threat-detection-engineer`, `llm-finops-architect`. Um keyspace de 12 não REPRESENTA esse
mapa, logo a W-ROTA não poderia migrá-lo — o keyspace da tabela é a união de TODOS os mapas
do censo, derivada no LAND e nunca digitada.

**Errata do rail r9 (P1): a chave tem DUAS dimensões, não uma.** `task-route.py:534-542` roteia
`devops` para `claude-opus-4-8` **só quando `workflow_change ∈ {release, ci}`**, enquanto o pin
default do papel é Sonnet e os perfis de qualidade variam de forma independente. Uma chave
só-papel não PRESERVA esse comportamento ao tornar `task-route.py` leitor — ou colapsa o
contexto (perde a regra) ou duplica a linha (dois `model_id` para a mesma chave). O r6 acertou que
`task-route.py` não LÊ a superfície (4a); o r9 mostra que ele é **dono LOCAL de um mapa
CONTEXTUAL próprio** (papel × sinal → modelo, com id JÁ DEFASADO `claude-opus-4-8` em `:538`) —
a sétima grafia do mesmo fato, e uma que a lista de leitores do r6 tinha deixado de fora.
Reclassificação: `task-route.py` sai de «leitor de (4a)» e entra como «dona local (5) — mapa
contextual». A tabela ganha a coluna `task_context` (`*` = qualquer), e a linha `devops` vira duas:
`(devops, *) → sonnet-pin` e `(devops, release|ci) → opus`.

Colunas mínimas: `role` × `task_context` (chave composta: `role` = a UNIÃO derivada de TODOS os mapas
do censo — `agents/*.md`, `routing-matrix.yaml`, `_ADR_052_ROLE_TO_MODEL`,
`templates/.claude/tier-policy.json`, o mapa contextual de `task-route.py`; `task_context` = o sinal
do roteador ou `*`), `model_id` (id COMPLETO do alvo EXATO, para `agents/*.md` e
`VETO_HARDCODE`; `-` nos papéis só-matriz), `matrix_floor` (tier MÍNIMO `opus|sonnet` para
`coder_model` — errata do rail S340: um alvo exato NÃO se converte em piso por prefixo de
família, `claude-fable-5` não é família `opus` e o loader exige `coder_model == "opus"` nos
papéis VETO, `routing-matrix-loader.py:581-585`; alvo e piso são dois fatos), `veto_role`
(bool — autoridade de PAPEL, fonte `VETO_FLOOR_ROLES`/frontmatter; errata do rail S340 r3:
`VETO_FLOOR_ALLOWED` diz que MODELOS podem servir um VETO, não que papéis TÊM VETO — derivar o
bool de membership promoveria QA/perf/devops a VETO quando `set-quality-profile.sh max-quality`
lhes dá Opus; a validação `model_id ∈ VETO_FLOOR_ALLOWED` é um check SEPARADO), `reason`,
`adr_ref`. Mais uma SEGUNDA relação `skill_tier` (skill → tier `opus|sonnet`), porque o
`MODEL_HINT` seleciona por `DETECTED_SKILL` sobre qualquer persona dos mapas (§1), não por
papel. Leitores: (1) e (4a) a coluna `model_id`, (3) a coluna `matrix_floor`, (2) a relação
`skill_tier`; nenhuma fica com o dado duplicado. **Dimensão de PERFIL (rail r4, P2):**
`set-quality-profile.sh:157-169` escolhe Opus/Sonnet/Haiku para QA, perf e devops POR PERFIL
(`max-quality`, …); um `model_id` único por papel não o representa — a fonte precisa de uma
relação de override `(profile, role) → model_id` (ou coluna `profile`, com `default` como
linha base), senão o script mantém um mapa local ou perde o comportamento por perfil. Esta é PROPOSTA — não landa nesta wave (US5 é só o censo; a tabela é entregável da
wave W-ROTA, OQ-7, decidida para DEPOIS da W1 per `PLAN-186-orchestrator-operating-model.md`
linha "US5 (nova, C-K1)").


> **Errata do rail r25 (P2):** a afirmação «nenhuma superfície é cruzada mecanicamente com a
> autoridade da frota» é FALSA em uma aresta: `.claude/hooks/tests/test_veto_floor_bijection.py:159-173`
> parseia o frontmatter de `agents/*.md` e assevera que todo `veto_floor: true` tem `model` ∈
> `VETO_FLOOR_ALLOWED`. É a ÚNICA aresta mecânica pin→frota hoje, e a W-ROTA tem de PRESERVÁ-LA
> (a tabela única vira a fonte que esse teste lê, não um substituto que o apaga).
