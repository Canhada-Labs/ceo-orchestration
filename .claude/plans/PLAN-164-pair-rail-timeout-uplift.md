---
id: PLAN-164
title: Pair-rail liveness — timeout uplift + re-âncora do GATE-V2
status: done
created: 2026-07-29
executing_since: 2026-07-29
completed_at: 2026-07-30
related_commits: [8f21b25, 35fad10, 7628a97, 2761462, 341ffc3]
reviewed_at: 2026-07-29
reviewed_by: "Owner (João) — tie-break estruturado S285: OQ1=120s / OQ2=150s / OQ3=mecânica-do-pin / OQ4=delta-1-round (todas nas recomendações do consenso round 1)"
owner: CEO
depends_on: [PLAN-163]
budget_tokens: 60-120k
budget_sessions: 2
context_risk: low
external_wait: none
tags: [pair-rail, hooks, kernel, incident, gates]
---

# PLAN-164 — Pair-rail liveness: timeout uplift + re-âncora do GATE-V2

## Context

Incidente formal ratificado pelo Owner em S285 (2026-07-29, opção C do
tie-break). Evidência completa em
`.claude/plans/PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md`:

- O default `CEO_PAIR_RAIL_TIMEOUT_S=30` é estruturalmente menor que a
  latência real de um verdito codex in-hook: **36,3 s medidos** com prompt
  realista (gpt-5.6-sol, reasoning xhigh; 8,3 s num round trivial pelo
  MESMO binário pinado ADR-182).
- **12 de 12 `pair_rail_case` na história inteira do audit-log são
  F/TIMEOUT** — o rail nunca completou um review vivo. O pin do PLAN-163
  corrigiu integridade (payload/verify-then-invoke, self-check OK), não
  latência.
- O log é append-only (HMAC): o case-F do probe fresco de 2026-07-29 tornou
  `failopen==0` insatisfazível contra a âncora atual
  (`a4371c7` / 2026-07-29T10:16:16-03:00) — o GATE-V2 do PLAN-163 exige
  RE-ANCORAR além do fix.
- O main-pack staged do PLAN-163 NÃO toca `check_pair_rail.py` (0 hits no
  MANIFEST), mas CONTÉM `settings.json` + `templates/settings/*` com a
  registration em `timeout: 60` — o fix de kernel exige sincronizar o pack
  congelado (senão a cerimônia do pack REVERTE o timeout), com re-review
  delta dos bytes mudados.

Colateral fora de escopo: `stop_review` nudge-only transiente (S284).

## Goal

O rail completa reviews vivos com margem honesta (healthy cases A-E
observáveis), o GATE-V2 do PLAN-163 é re-ancorado e passa, e a cerimônia do
main-pack fica desbloqueada.

## Approach

Uma cerimônia única (Owner, GPG, `CEO_KERNEL_OVERRIDE`) sobe o budget
interno do hook E o teto da registration no harness, com paridade de
templates e sync do pack congelado; a própria cerimônia re-ancora o
GATE-PIN-ANCHOR; prova fresca em sessão nova fecha o gate. Alternativa
rejeitada: env-knob por sessão (opção B do tie-break) — não corrige o
default da frota (adopters seguem 100 % fail-open) e a prova não valeria
para a configuração shipada.

Classificação: **L3+** (security rail + kernel settings.json). **Debate
round 1 EXECUTADO em 2026-07-29: 3× ADJUST → PROCEED** (consenso em
`PLAN-164/debate/round-1/consensus.md`; ajustes C1-C5 + kept-1..8
incorporados abaixo).

**Registro: AMEND-1 do ADR-110** (pretool enforcement — contrato operativo
do rail), cross-ref ADR-106. NÃO um ADR de número novo — restrição dura
verificada pelo debate: o número ADR-183 já está consumido por bytes
double-APPROVEd do pack congelado. **Correção W1 (verificada na
execução):** a convenção da casa materializa AMENDs como ARQUIVO SEPARADO
(`ADR-NNN-AMEND-M-slug.md`, 17 precedentes) — o arquivo
`ADR-110-AMEND-1-rail-timeout-contract.md` MOVE a contagem de arquivos
181→182 (a premissa original do debate, "amend não muda contagem", valia
para amend-in-place, que não é a convenção). Consequência absorvida no
pack: o rail-pack também stage-ia `land-plan163-pack.sh` com os gates
fail-closed de contagem bumpados (pré-apply 182 / pós-apply 184, expect
dict e closeout em sincronia) e o closeout do rail faz o sweep de docs
181→182 (sed list impresso pela cerimônia). O pack congelado não contém
cópia staged do ADR-110, então o amend vivo sobrevive ao apply. O amend
nomeia:
residual do env-knob sub-piso (auditável via case F), o gatilho de
recalibração (≥10 healthy → p95 de `case.ts − expected.ts` revisita os
números), as alternativas rejeitadas (review assíncrono pós-facto — o valor
do rail é o veto pré-write; downgrade de reasoning-effort — qualidade
não-validada), a nota do `check_codex_filewrite.py` timeout 30 (próximo
"default 30" escondido se o review migrar para MCP), e a semântica de
overflow do clamp.

## Waves

### W0 — Ratificação de parâmetros (Owner tie-break)
Check: none (doc-only)
- [x] Protocolo de medição (consenso C5) EXECUTADO 2026-07-29: N=9 —
  small idle 25,8/33,3/34,9/36,3/38,8/68,8 s; big idle 15,4 KB 58,4/51,3 s;
  small sob carga **75,1 s**. p95≈75 s > 70 s → escalada do protocolo:
  **interno 120 / registration 150**.
  Check: none (doc-only — dataset registrado aqui e no consenso)
- [x] OQ1-OQ4 RATIFICADAS pelo Owner (tie-break estruturado, 2026-07-29):
  **OQ1 = "120 s"** / **OQ2 = "150 s"** / **OQ3 = "Mecânica do pin"**
  (âncora pós-commit `[SENT-PLAN164-RAIL]` + closeout imediato +
  resolve_anchor fail-closed) / **OQ4 = "Delta 1 round"** (com prova
  mecânica da negativa) — todas as quatro na opção recomendada do
  consenso. Literais 120/150 são os valores normativos dos ACs de W1.
  Check: none (doc-only)

### W1 — Staging + testes (nada toca a árvore canônica viva)
- [x] Staged `check_pair_rail.py`: default `"30"` → literal OQ1 no
  `os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", ...)` (~L1717), fallback
  `timeout_s = 30.0` (~L1720/1722) e docstring (~L51-52); clamp `>600`
  mantido. Check: `python3 -m pytest .claude/hooks/tests/ -k pair_rail -q`
  verde no overlay de staging.
- [x] Staged kernel `settings.json`: registration do `check_pair_rail.py`
  `timeout: 60` → literal OQ2 + `_comment` "(default 30s)" atualizado.
  Check: oracle hook-stdout-schema + settings-parity verdes no overlay.
- [x] Paridade de template: `templates/settings/settings.base.json`
  (registration ~L97) mesmo timeout OQ2. Check: diff mecânico das duas
  registrations idêntico (mesmo valor), suíte de parity verde.
- [x] Sweep de testes que assertam o default antigo (30/60): atualizar
  espelhos + adicionar teste explícito do valor default novo.
  Check: `grep -rn "TIMEOUT_S" .claude/hooks/tests/` não retorna
  asserções do valor antigo; suíte cheia verde.
- [x] Sync do pack congelado PLAN-163 na ORDEM NORMATIVA (consenso C3, a
  única sequência que não aborta o preflight): (0) commitar o gêmeo
  `inputs-pack.sha256` do estado R6 ATUAL — baseline tamper-evidente; o
  gêmeo NÃO existe hoje → (1) editar os arquivos staged do delta →
  (2) recomputar `staged/main-pack/MANIFEST.sha256` → (3) delta-review
  sobre os bytes FINAIS → (4) review mudou byte? volta a (2) →
  (5) regenerar gêmeo + 2º commit. Diff dos gêmeos limitado às entradas
  pretendidas (linha extra = ABORT); sha antigo→novo por arquivo no
  artefato de review.
  Check: `shasum -c` dos manifests PASS; diff dos dois gêmeos tracked ==
  exatamente as entradas do delta; artefato de review delta commitado em
  `PLAN-163/review/`.
- [x] Teste de invariante entre camadas (consenso C2): parseia
  `settings.json`, `templates/settings/settings.base.json` e o default
  literal do hook; asserta registration kernel == registration template E
  `registration ≥ interno + 30`. Roda na suíte e no overlay do preflight
  do pack.
  Check: teste novo verde; vermelho se qualquer literal flipar
  unilateralmente (provar com mutação local dos 3 valores).
- [x] Migração de adopter (consenso C4-ii): passo idempotente no
  settings-merge do `scripts/upgrade.sh` — bump da registration do
  `check_pair_rail.py` 60→150 IFF valor atual == 60 (custom preservado);
  check no `scripts/doctor.sh` (warn se registration < interno + 30); caso
  novo na família `test_upgrade_settings_migration.py`.
  Check: fixture de upgrade 2× (idempotência) verde com o bump aplicado
  exatamente uma vez; doctor.sh warn provado com fixture 60/120.
- [x] Guard de aposentadoria do pin-pack (consenso C4-i): o APPLY de
  `land-plan163-pin.sh` passa a morrer se `git log
  --grep='\[SENT-PLAN164-RAIL\]'` encontrar o commit ("pin superado pelo
  PLAN-164; só --gate-v2 permanece válido") — o pin-pack staged contém
  `check_pair_rail.py` com default velho e re-apply reverteria o fix com
  preflight verde.
  Check: guard provado (com o commit presente, apply aborta; --gate-v2
  segue funcionando).
- [x] UX + comments (consenso kept-5 + Critic-C): `statusMessage` na
  registration do pair-rail (kernel + template + cópias staged do pack,
  ex.: "Pair-rail cross-model review — pode levar 1-2 min"); atualizar
  `_comment` "(default 30s)" no kernel E template; sweep de literais no
  repo INTEIRO + `staged/` inteiro (fora de hooks+settings a varredura do
  debate achou 0 hits em docs — confirmar mecanicamente).
  Check: grep repo+staged sem ocorrências do par 30/60 nas superfícies do
  rail; statusMessage presente nas 4 cópias.

### W2 — Cerimônia (Owner-run via `!`, GPG)
- [x] Fix do `resolve_anchor()` (consenso C1; revisado no r2 do review):
  âncora tratada como PONTEIRO — `ts` derivado de `git log -1 --format=%cI
  <sha>` (nunca lido do arquivo); `sha` deve ser um commit de CERIMÔNIA
  (subject TERMINANDO em `[SENT-PLAN163-PIN]` ou `[SENT-PLAN164-RAIL]` —
  a regra de sufixo mata o vetor de laundering por menção no meio da
  mensagem, e mensagens de closeout/rollback nunca carregam o tag);
  fallback (arquivo ausente) = o commit de cerimônia MAIS NOVO, o que
  mantém a recuperação pós-revert possível (o canonical-oldest do r1
  criava deadlock — codex r2 HIGH-1); qualquer falha → die (fail-closed,
  sem command substitution). Script em `PLAN-163/` (não-canônico).
  Check: com âncora adulterada (ts movido / sha não-sentinel), `--gate-v2`
  ABORTA; com âncora íntegra, resolve normal.
- [x] Sentinel round novo (escopo exato = arquivos do W1 vivos); apply sob
  `CEO_KERNEL_OVERRIDE`; commit assinado `[SENT-PLAN164-RAIL]`.
  Check: `touched − scope = ∅`; suíte pós-apply verde.
- [x] Re-âncora na MECÂNICA DO PIN (consenso kept-3 — um commit não contém
  o próprio sha): pós-commit da cerimônia, escrever
  `.claude/plans/PLAN-163/GATE-PIN-ANCHOR` com sha+ts do commit
  `[SENT-PLAN164-RAIL]` e commitá-la no closeout IMEDIATO (arquivo já é
  tracked). Transparência declarada no Scope do sentinel.
  Check: `land-plan163-pin.sh --gate-v2` imprime a âncora nova e validada.
- [x] DISCIPLINA DA JANELA DE ASSIMETRIA (consenso kept-2): pós-apply, na
  sessão da cerimônia, NENHUM Edit/Write/MultiEdit em path canônico —
  closeout inteiro via `!`/bash (interno novo vale por-invocação;
  registration 150 só vale pós-restart; um edit canônico nessa janela vira
  deficit pós-âncora e re-envenena o gate). FREEZE de edits canônicos em
  TODAS as sessões até o W3 PASS registrado.
  Check: none (doc-runbook — disciplina operacional declarada no sentinel)
- [x] Closeout: claims + verify-counts + push + Validate.
  Check: `gh run watch` do Validate = success.

### W3 — Prova fresca + desbloqueio do PLAN-163
- [x] Sessão NOVA (a registration nova só vale pós-restart do harness);
  probe bytes-idênticos (padrão S281) → case A-E esperado.
  Check: `land-plan163-pin.sh --gate-v2` = PASS (expected≥1 ∧ healthy≥1 ∧
  failopen==0 ∧ unclassified==0 ∧ deficit==0 pós-âncora-nova).
  **EXECUTADO 2026-07-30 (S286): case=A (PASS/PASS), review vivo em
  115 s — 1º healthy em 13 invocações da história; gate PASS 1/1/0/0/0.**
- [x] Registrar o PASS em `PLAN-163/probes/` com a semântica EXPLÍCITA
  (consenso kept-8): o gate re-ancorado prova "liveness sob pin ADR-182 +
  timeout novo" — estritamente mais forte que a prova original (o pin não
  foi tocado); registrar para o leitor futuro não concluir que a prova do
  pin nunca existiu. Check: arquivo commitado.
  **→ `PLAN-163/probes/GATE-V2-2026-07-30-PASS.md`.**
- [x] Handoff: PLAN-163 Passo 4 (cerimônia do pack) liberado com
  `--confirm-gate-pin-done --confirm-gate-v2-fresh` verdadeiras.
  Check: none (executa no PLAN-163).

## Open questions (pós-debate round 1 — pendentes de ratificação do Owner)

- **OQ1 — default interno novo. Draft pós-medição: 120 s** (era 100 no
  draft pré-debate; a medição C5 — N=9, p95≈75 s incluindo 75,1 s sob
  carga — cruzou o limiar de 70 s do protocolo e acionou a escalada
  definida pelo próprio debate). Clamp 600 mantido. Os 3 críticos
  rejeitaram 48/minimal-change como a mesma classe de aposta que produziu
  o 30.
- **OQ2 — registration do harness. Draft pós-medição: 150 s** (interno 120
  + 30 s de margem absoluta — restaura a margem pré-uplift; precedente de
  registration >120 já existe no kernel: `codex_review_user_code.py`
  timeout 130). Condicionada ao teste de invariante C2 (W1). Custo de UX
  aceito pelos críticos: a alternativa real não é "review mais rápido", é
  "nenhum review"; mitigado por `statusMessage` (W1).
- **OQ3 — mecânica da re-âncora. RESOLVIDA pelo debate** (ratificação
  formal pendente): mecânica do pin — âncora escrita PÓS-commit da
  cerimônia com sha+ts de `[SENT-PLAN164-RAIL]`, commitada no closeout
  imediato; `resolve_anchor()` validando ponteiro fail-closed (C1).
  Re-rodar `land-plan163-pin.sh`: REJEITADO pelos 3 críticos (reverteria o
  fix — o pin-pack staged contém `check_pair_rail.py` com default 30; fato
  de manifest) → guard de aposentadoria no W1.
- **OQ4 — profundidade do re-review do pack. Draft mantido: delta-confirm
  1 round**, condicionado à prova mecânica da negativa (C3: gêmeo baseline
  commitado antes do sync; diff dos gêmeos == exatamente o delta; sha
  antigo→novo por arquivo). Full re-review rejeitado como custo sem ganho
  (S284: 17,5M tokens).

## Progress log

- **2026-07-30 (S286, W3 EXECUTADO — PLANO DONE):** sessão nova; probe
  bytes-idênticos (S281, `cmp` provado, canonical guard bloqueou — árvore
  intacta) → **case=A (claude=PASS, codex=PASS), review vivo em 115 s —
  o 1º healthy em 13 invocações da história do log**. `land-plan163-pin.sh
  --gate-v2` = **PASS** (post-anchor 1/1/0/0/0; self-check ADR-182 OK;
  âncora `35fad10` validada fail-closed). Registro kept-8 em
  `PLAN-163/probes/GATE-V2-2026-07-30-PASS.md`. Nota de recalibração:
  115 s ≫ p95≈75 s medido — margem real ~5 s; gatilho ≥10 healthy do
  AMEND é prioritário. PLAN-163 Passo 4 (pack) LIBERADO
  (`--confirm-gate-pin-done --confirm-gate-v2-fresh`).
- **2026-07-30 (S285→S286, W2 EXECUTADO — cerimônia Owner):** tooling
  pré-cerimônia `8f21b25` (resolve_anchor suffix-newest revert-aware
  fail-closed + retirement guard + count-gates 182/184); cerimônia GPG
  `35fad10` `[SENT-PLAN164-RAIL]` (touched−scope=∅); re-âncora
  `7628a97` (closeout imediato, ADRs 182); sweep de superfícies
  `2761462` (COMMAND-SKILL-HOOK-MAP). Janela de assimetria respeitada
  (closeout inteiro via bash, zero edits canônicos). Validate = success
  em `7628a97` e `2761462`.
- **2026-07-29 (S285, W1 EXECUTADO):** staging completo via workflow
  (8 builders + 2 verifiers, opus) + fix agent. Rail-pack final = 8
  arquivos (MANIFEST + gêmeo tracked `inputs-rail.sha256`). Dois achados
  estruturais corrigidos em voo: (a) convenção da casa faz o AMEND ser
  ARQUIVO (17 precedentes) → contagem 181→182 → pack-script staged com
  gates 182/184 entrou no rail-pack e o closeout do rail ganhou o sweep
  181→182; (b) clobber cross-pack em `scripts/upgrade.sh` (main-pack
  congelado carrega a maquinaria T5.4) → migração movida para o upgrade.sh
  DO main-pack (cap derivado do template em runtime; 36/36 verde no
  overlay combinado), rail-pack ficou sem upgrade.sh; doctor.sh ficou
  (sem clobber). Baseline R6 do pack commitado ANTES do sync (`341ffc3`,
  ordem C3). Preflight-only do `land-plan164-rail.sh`: PASSED fim-a-fim
  (twin, scope set-equality 8/8, value-gate 120/150/statusMessage,
  oráculos overlay verdes). Validate red em `341ffc3` = flake xdist-race
  de `__pycache__` no copytree (4 errors, 10.284 passed) — rerun
  disparado. Review cross-vendor r1 (codex+grok) em execução sobre os
  bytes finais.

## How to continue

Sessão nova: Gate 1-3; ler este plano + o diagnóstico em
`PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md` + o consenso em
`PLAN-164/debate/round-1/consensus.md`. Debate round 1 já EXECUTADO
(3× ADJUST → PROCEED, ajustes aplicados). Se `status: draft`: ratificar
OQ1-OQ4 com o Owner → `reviewed`. Se `reviewed`: executar W1 (staging +
testes), depois cerimônia W2 via `!` (Owner) e prova W3 em SESSÃO NOVA
(registration só vale pós-restart) — respeitando o freeze de edits
canônicos até o W3 PASS.

## Success criteria

- [x] GATE-V2 do PLAN-163 = PASS registrado sob a âncora nova.
- [x] Rail com pelo menos 1 case healthy (A-E) real no audit-log — o
  primeiro da história do log.
- [x] Paridade dogfood ↔ template mantida; pack congelado sincronizado com
  manifests self-consistentes e re-review delta registrado.
- [x] Suíte + Validate verdes; claims/verify-counts sem drift.
- [x] Nota honesta: o row 168h do ceo-boot segue RED até os 12 case-F
  antigos saírem da janela (~2026-08-05) — esperado, registrar e ignorar
  (mesma nota do runbook do PLAN-163).

## Owners / Blockers / Next

- **Owner:** CEO (execução) + Owner humano (tie-breaks OQ1-OQ4, GPG W2).
- **Blocker atual:** NENHUM — plano DONE 2026-07-30 (W3 PASS registrado).
  **Review cross-vendor: APPROVE DUPLO no r6** (2026-07-29; 6 rounds,
  ~20 findings reais aplicados — r1: 12 incl. 2 vetores de laundering da
  âncora; r2: deadlock pós-revert do canonical-oldest; r3: rollback
  CI-red + âncora-revertida-válida; r4: validador se auto-revertia com a
  cerimônia → split estrutural, tooling pré-cerimônia `8f21b25`; r5:
  consistência do payload de assinatura; r6: limpo. Verditos em
  `PLAN-164/review/`).
- **Next (executa no PLAN-163):** cerimônia do main-pack via
  `land-plan163-pack.sh` com `--confirm-gate-pin-done
  --confirm-gate-v2-fresh` (ambas verdadeiras desde
  `PLAN-163/probes/GATE-V2-2026-07-30-PASS.md`); resolver os 2 P2 de
  pricing ANTES do commit W2 do pack. Follow-up deste plano: gatilho de
  recalibração do ADR-110-AMEND-1 quando houver ≥10 healthy (1ª amostra
  vivo = 115 s, margem ~5 s sob o budget de 120 s).
