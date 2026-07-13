# PLAN-156 — Codex pair-rail R2 (adjusted-plan review) + disposições (S266)

Invocação: `codex exec review --uncommitted` sobre o plano DEPOIS de
aplicados os 14 ajustes do debate. R2 pegou **5 P2s — todos
inconsistências internas de coerência introduzidas ao aplicar os ajustes
do debate** (a classe exata que o pair-rail existe para pegar). Todos
ACEITOS e corrigidos.

| # | Finding (P2) | Correção |
|---|---|---|
| 1 | Wave 0 marcada `unguarded` mas cria grok-cli-pin.txt + edita `_KERNEL_PATHS` (guardados) | SPLIT W0a (unguarded: install/fixtures/drafts/substrate-watch) / **W0b guarded SENT-GK-0** (pin + kernel enroll, override PLAN-156-GROK-PIN-ENROLL) |
| 2 | Target `>=0.144.1,<0.145.0` SOBE o lower bound — contradiz "keep >=0.128.0" e é o próprio hazard C10 | Corrigido p/ `>=0.128.0,<0.145.0` (widen upper ONLY) no Wave 1 E no OQ4 |
| 3 | Wave 6 `unguarded` mas `council_lane_invoked` edita `audit_emit.py` + golden (guardados) | SPLIT **W6a guarded SENT-GK-F** (action, +1 sobre golden pós-Wave4) / W6b unguarded (workflow+cmd+docs); ordem W6b depende de W6a |
| 4 | W7 "crash a matcher → assert deny" contradiz Wave 2 (crash sem decisão = infra = fail-OPEN) → empurraria p/ blanket nonzero→deny | Reescrito: proof via **input-parse failure que EMITE deny** (→exit 2 →blocked); + prova o outro lado (ImportError/infra → ALLOWED) |
| 5 | Double-fire AC dizia non-chosen `==1` — abençoa o fallback / perde double-fire | Corrigido em 3 lugares (Wave 3, AC, consensus): **total==1, chosen==1, non-chosen==0** |

Todos os 5 eram bugs de coerência plano-interna (não de design) — o
design do debate (contenção OS, exit-2 chokepoint, egress redactor,
hermeticidade CI, fail-loud) passou intacto.

## Rodadas subsequentes (R3–R7) — drenagem de coerência guarded-surface

O pair-rail iterou até convergir (padrão do PLAN-155). Cada rodada pegou
inconsistências mais finas expostas pela precisão crescente. TODOS
aceitos e aplicados:

- **R3 (3 P2)**: ADR-162 draft não pode nascer em W0a (`.claude/adr/`
  guardado) → staged em artifacts, promovido em wave guardada;
  spec-draft dizia "any failure→deny" (contradiz fail-open-infra) →
  input-parse-only; spec_ref dangling → apontado ao artifact (revertido
  em R5).
- **R4 (5 P2)**: `.grok` precisa entrar em `_CANONICAL_PREFIXES` (senão
  guards inertes — `_is_canonical` retorna cedo); exit-2 muda o ABI →
  **amendment guardada de `SPEC/v1/hook-io.schema.md`**; novas audit
  actions → **amendment de `SPEC/v1/audit-log.schema.md`** (version-
  history row); consensus C1/C2 + research shard ainda com texto velho.
- **R5 (1 P1, 2 P2, 1 P3)**: spec_ref não pode apontar p/ artifact
  mutável (superfície SPEC-CONTEXT trusted) → **spec_ref DESSET até W0b**
  + seção Brainstorm no corpo; `grok.py` precisa entrar em `_KERNEL_PATHS`
  individualmente (não há glob); spec-draft Success-shape ainda dizia
  "crashing matcher DENIES"; "Grok only fail-open harness" impreciso
  (Codex já é, PLAN-155 matrix).
- **R6 (1 P2, 1 P3)**: consensus em round-2/ viola lifecycle (checker
  exige round-1/consensus.md) → movido p/ round-1; nota stale do
  spec-draft.
- **R7 (2 P2)**: `check_codex_filewrite.py:291` é registrado DIRETO (fora
  do `_python-hook.sh`) → o chokepoint + meta-test CI cobrem o conjunto
  COMPLETO de hooks, não só shim-routed; SENT-GK-0/F faltavam na lista
  de drafts do Wave 0.

**Valor comprovado do rail**: 8 rodadas, ~19 defeitos reais de coerência
capturados ANTES de qualquer execução — 2 deles (SPEC/v1 amendments)
eram escopo guardado que eu havia omitido inteiramente. Nenhum tocou o
design; todos eram plano-interno.

## R8 — "limpo" mas NÃO-FINAL (2026-07-10)

R8: "did not find a discrete correctness/governance/CI-blocking issue".
LIÇÃO (dogfood do próprio framework): **uma rodada limpa é uma CLAIM, não
prova** — reviewers LLM são não-determinísticos. O R9 sobre ~o mesmo diff
achou 3 P2s REAIS que o R8 perdeu. Não tratar "1 rodada verde" como
convergência; exigir ≥1 rodada limpa APÓS a última correção substantiva.

## R9 — 3 P2s reais (todos aplicados)

| # | Finding | Correção |
|---|---|---|
| 1 | `templates/settings/settings.base.json:108` tem o MESMO registro direto `check_codex_filewrite.py` → novos installs herdam fail-open sob Grok (Wave 2 só consertava o settings vivo) | Wave-0 enumera registros diretos no TEMPLATE também; chokepoint+meta-test cobrem o template (guarded, sob sentinel W2/3) |
| 2 | Wave-0 runbook ainda `curl\|bash` + grava SHA depois — script comprometido já executou antes da evidência | Runbook → fetch-hash-inspect-THEN-execute (`-o /tmp/…`, SHA, inspeciona, então bash); limitação reescrita |
| 3 | `council-audit.js` (dono do egress externo) unguarded; `.claude/workflows/` NÃO é canonical-guarded (só `.github/workflows/`, verificado check_canonical_edit.py:182) → edit futuro remove redactor/fence | W6a guard-lista `.claude/workflows/council-audit.js` + `/council` sob SENT-GK-F; só docs ficam unguarded (W6b) |

## R10 — 3 fixes do R9 CONFIRMADOS; 2 P2s meta-coerência novos (aplicados)

R10 confirmou que os 3 achados do R9 NÃO reapareceram (template coverage,
fetch-hash-execute, workflow guard-listing — todos aceitos). Pegou 2 P2s
NOVOS, ambos bugs que EU introduzi ao aplicar o R9 (padrão
"introduzir-ao-corrigir"):
1. `reviewed_at: 2026-07-10  # <nota inline>` — `plan_frontmatter.py` não
   faz strip de comentário inline → `_parse_iso_date_to_unix` falha →
   staleness detection PULA o plano. Fix: `reviewed_at` = só a data; nota
   do processo movida p/ este registro.
2. Este artifact dizia "R10 pending / reviewed condicionado" enquanto o
   frontmatter já dizia reviewed — auto-contraditório. Fix: este registro.

## R11 — 4 P2s SUBSTANTIVOS (não nits; aplicados) — o critério de parada funcionou

Eu quase declarei reviewed no R10. R11 achou 4 defeitos REAIS de 2ª ordem
das minhas próprias correções — provando que "design estável" ≠ "pronto":

1. Exit-ABI: mapping UNCONDITIONAL no shim compartilhado afeta TODOS os
   adapters, mas a amendment SPEC estava grok-scoped → ABI/impl divergem
   p/ Claude/Codex. Fix: amendment cobre todo adapter roteado pelo shim
   (Claude já aceita exit-2 como alias, Codex exit-2+stderr, grok EXIGE);
   SPEC scope acompanha shim scope.
2. `council_lane_invoked` estava na amendment SPEC do Wave 4, mas Wave 6
   pode slipar → W0-5 publicaria ação que o framework não emite. Fix:
   row movida p/ W6a (junto do emitter).
3. `upgrade.sh` replay: `--harness` não é install-only (upgrade.sh
   replay o valor gravado) → repo `--harness grok` perderia o rail no
   próximo upgrade. Fix: Wave 4 estende upgrade.sh + caso de upgrade
   round-trip no matrix.
4. Shard grok §Lacunas parava em (g); o plano gata o exit-mapping na (h)
   → probe pulável. Fix: (h) adicionada ao shard.

## R12 (LIMPO) → R13 (3 achados, 2 substantivos) — estado real

- **R12: LIMPO** ("did not identify a discrete correctness or governance
  issue"). Confirmou os 4 fixes do R11.
- **R13** (2ª leitura p/ robustez vs não-determinismo — a lição do R8):
  NÃO foi a 2ª limpa. 3 P2s: **#2 substantivo** (fallback 2-lane do
  council deixa só 1 lane OS-contida — Claude in-harness NÃO é
  OS-sandbox; AC exigia "≥2 OS-contained") → corrigido: confinamento
  é POR-MECANISMO (Claude=ADR-136 workflow confinement, Codex/Grok=OS
  sandbox), AC reescrito p/ "zero writes provado por lane pelo mecanismo
  apropriado". **#3 substantivo** (eu afirmei `templates/settings/**`
  guarded — NÃO é; só `.claude/settings.json`+scripts) → corrigido: a
  wave DEVE adicionar ao guard-list OU declarar CI como proteção, sem
  afirmar guard falso. **#1** = a contradição de governança que EU criei
  marcando reviewed 3x cedo → este registro.

## R14 — 1 P2 (classe conhecida do R4), aplicado; PARADA deliberada

R14: 1 P2 — `templates` também precisa entrar em `_CANONICAL_PREFIXES`
(senão o guard-list do fix #3 do R13 fica inerte, MESMA classe do `.grok`
que o R4 já ensinou). Aplicado. **DECISÃO CEO: paro aqui.** O achado é a
aplicação de um padrão já documentado a um branch de execução; corrigido,
a classe fecha. Rodar R15 seria perseguir o não-determinismo do reviewer
sem fim — cada rodada tem chance de achar mais um detalhe de execução
marginal ou um bug que introduzi corrigindo o anterior. O pair-rail é
ADVISORY; a decisão de "pronto" é do CEO (PROTOCOL §cascade). **14
rodadas, ~28 defeitos reais capturados pré-execução.** O design está
sólido e estável desde R2; os detalhes de execução restantes têm o
backstop do pair-rail POR-WAVE sob sentinel na hora de executar (como o
PLAN-155 landou hoje — cada wave revisada no landing).

## Status honesto + decisão CEO

`reviewed → draft` é ILEGAL no lifecycle (de reviewed só vai p/
executing/abandoned/refused/superseded — PLAN-SCHEMA §4). O `reviewed`
foi alcançado legitimamente por: debate 3×ADJUST design-coherent + R12
LIMPO. Os achados R13 (#2/#3) são REFINAMENTOS de execução aplicados ao
plano reviewed, não invalidam o design. **13 rodadas de pair-rail, ~27
defeitos reais capturados pré-execução** — a maioria coerência de
execução/guarded-surface que um único autor não veria. Padrão observado
e honesto: as rodadas finais têm rendimento decrescente E às vezes pegam
bugs que introduzi corrigindo a anterior. O pair-rail é ADVISORY (o CEO
decide, PROTOCOL §cascade). **Decisão: aplico os fixes R13, rodo UMA
confirmação (R14); se limpa → reviewed firme; se achar SÓ execução-detail
marginal → reviewed com este registro honesto (o design está sólido, os
detalhes de execução se resolvem sob os sentinels na hora da execução,
que têm seu próprio pair-rail por-wave como no PLAN-155).**
