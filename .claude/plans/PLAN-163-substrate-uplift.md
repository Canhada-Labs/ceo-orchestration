---
id: PLAN-163
title: Substrate uplift — reconcile CC 2.1.198→2.1.220 + Claude 5 family (Opus 5 / Sonnet 5) adoption
status: done
created: 2026-07-27
reviewed_at: 2026-07-27
executing_since: 2026-07-28
completed_at: 2026-07-30
related_commits: [55e8e27, a4371c7, 7860d62, e540cd9, 341ffc3, 9477bde, 8ed9f6f, 3bce87c, 1241795]
reviewed_by: "Owner (João) — chat directive S281/S282 (montar plano + debate + review codex/grok); debate 3×ADJUST→PROCEED; cross-vendor codex r5 APPROVE + grok APPROVE"
owner: CEO
depends_on: [PLAN-161]
budget_tokens: 250-350k
budget_sessions: 3 (4ª pré-autorizada se o re-record de fixtures não for mecânico)
context_risk: medium-high
external_wait: none
tags: [substrate, models, hooks, parallelism, settings, installer, pins]
---

# PLAN-163 — Substrate uplift: CC 2.1.220 + família Claude 5

## Context

S281/S282 (2026-07-27/28). O ledger `substrate-watch.json` está reconciliado em
**Claude Code 2.1.198** (2026-07-01; verificação de schema mais recente: 2.1.202
via `docs/substrate-adopt-2026-07.md`), enquanto o CLI instalado é **2.1.220**.
Desde junho a Anthropic lançou a **família Claude 5 completa**: Fable 5
(2026-06-09, já adotado — VETO roles), **Sonnet 5** (2026-06-30, default do CC
desde 2.1.197; tokenizer novo ~+30% tokens; pricing intro $2/$10 até
2026-08-31, depois $3/$15) e **Opus 5** (2026-07-24, `claude-opus-5`, drop-in
no preço do Opus 4.8 $5/$25, 1M ctx default, effort `xhigh`, thinking
on-by-default, fast mode $10/$50, **bucket de rate-limit separado**). Fast mode
foi **removido do Opus 4.7** (agora só Opus 5/4.8). Opus 4.1 **retira em
2026-08-05**. Grok CLI instalado: **0.2.106** vs pin 0.2.93 (drift adicional
que o probe do T5.1 teria pego).

Fontes primárias: (a) sweep versão-a-versão do CHANGELOG oficial
2.1.199–2.1.220 com **verificação verbatim** das 4 claims mais perigosas;
(b) inventário file:line do repo (S281); (c) skill claude-api 2.1.220;
(d) `check-substrate-watch.py --probe-installed`.

**Governança deste plano até aqui:**
- **Debate round-1 (S281): 3×ADJUST → PROCEED, 14 ajustes**
  (`PLAN-163/debate/round-1/consensus.md`).
- **Review cross-vendor r1 (S281): codex REJECT (F1-F12) + grok REJECT
  (F1-F12)** (`PLAN-163/review/codex-r1.md`, `grok-r1.md`) — 24 findings, 6
  convergentes, aplicados. Destaques: o trio argparse NÃO está wired;
  GATE-V2 como "row verde" é vácuo (zero-expected→GREEN); allowlist de
  modelos é GERADA a partir do ADR-149; upgrade.sh não migra settings de
  adopters; enforcement do sha-pin é STUB em runtime; sha do payload nativo
  (`80a3933d…`) ≠ pin do launcher (`134063e1…`), provado pelas DUAS lanes.
- **Review cross-vendor até APPROVE (S281/S282), 5 rounds codex × 4 grok:**
  r1 codex REJECT(12) + grok REJECT(12) → r2 codex REJECT(7) + grok
  REJECT(3) → r3 grok **APPROVE** + codex REJECT(3) → r4 codex REJECT(1) →
  **r5 codex APPROVE + grok delta-confirm APPROVE** (`review/codex-r*.md`,
  `grok-r*.md`). Total: 38 findings aplicados. Destaques do ciclo: path
  REAL do payload é o pacote opcional de plataforma
  (`@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex`);
  enforcement obrigatório no RAIL VIVO com verify-then-invoke do MESMO
  path; **ADR-120 é o ADR de PII** (a cadeia "111→120" é inconsistência de
  ledger — locked-corpus manteve o id 111 per ADR-117): o pin ganha ADR
  NOVO; contrato do shim corrigido (é `exec` puro); espelhos independentes
  do ADR-149 (`validate-governance.sh:707-723`,
  `tier_policy_cli/_types.py:26-34`) no escopo; migração de upgrade
  baseline-aware com tabela normativa de literais por chave-folha.
  Nit ADR-level registrado (grok r4): wire-shape exato de triple+sha no
  envelope fica para o ADR novo do pin.

**Nota de conformidade (codex r1 F1):** este plano NÃO faz claims de
velocidade/throughput do framework (AGENTS.md). Onde o CHANGELOG do substrato
reporta mudanças de custo interno do CLI, o fato relevante para o plano é
apenas: *a base empírica do cap de concorrência (PLAN-083) foi medida em
substrato antigo e precisa de re-medição*. Nenhum número de speedup é
prometido ou herdado.

**Já absorvido (não re-fazer):** Fable 5 nos VETO roles (ADR-149); tier
Sonnet 5 em `tier_policy/_types.py` (ADR-157); eventos PreCompact/PostCompact
(ADR-153), Setup/init, ConfigChange, PostToolUseFailure wired; ToolSearch
(`ENABLE_TOOL_SEARCH=auto`); Workflow engine (ADR-136); turbo/accel layer;
lint `Write()` deprecado (PLAN-161 W1).

## Gap-matrix (substrato → framework)

| # | Mudança (versão) | Estado no framework (evidência) | Disposição | Benefício |
|---|------------------|----------------------------------|------------|-----------|
| G1 | `claude-opus-5` default Opus no CC (2.1.219); drop-in $5/$25; quota contabilizada em bucket separado | Allowlist é GERADA do ADR-149 (`AVAILABLE_MODELS_WORKING_SET`/`FALLBACK_MODEL_CHAIN`, `generate-available-models.py`, mirror test) — settings/templates são ESPELHOS; espelhos INDEPENDENTES adicionais: `validate-governance.sh:707-723`, `tier_policy_cli/_types.py:26-34`; routing/tier/agents em opus-4-8 | ADOPT via emenda ADR-149 + regen + espelhos (T1) | Capability uplift em debate/arch/VETO; contabilidade de quota separada (fato de compatibilidade) |
| G2 | `claude-sonnet-5` default do CC (2.1.197); tokenizer +30%; intro pricing até 08-31 | Tier existe (ADR-157) mas fora do working-set; advisory roles em sonnet-4-6 | ADOPT c/ contingência de default-flip (T1, OQ2, CF-6) | Advisory tier com custo por token menor (tabela pública); risco: budgets tokenizados +30% |
| G3 | Opus 4.1 retira 2026-08-05; fast-mode removido do 4.7 | `model-deprecations.json` fetched 2026-06-12 (stale). **Defeito de PRESENÇA real e vermelho HOJE:** `_PRICING_PER_MTOK` (audit-telemetry.py:39-45) sem opus-4-8 NEM fable-5; detectors `_LARGE_MODELS` sem fable-5. `ceo-cost.py`/`budget-summary.py`/`cost-table.yaml` JÁ têm opus-4-8/fable-5 (grok r1 F11) — neles só entram os ids NOVOS; `audit_log.py:890-917` é mapa role→model (routing, OQ1), não pricing. team.md `:578`/`:589` drifted | FIX presence-based, ADITIVO, escopo por superfície (T1) | Rollup de custo enxerga a frota corrente |
| G4 | Hooks exit-2 agora bloqueiam mesmo com stdout JSON inválido (2.1.214, verbatim) | **Nenhum dos hooks WIRED importa argparse** (codex r1 F2 + grok r1 F1); os 3 scripts argparse (check_harness_config, emit_architect_outcome, policy_dispatch) são CLI/CI ou unwired — `check_harness_config.py` DEVE manter exit≠0 (contrato validate.yml:960-984). Blocks intencionais = stdout-JSON exit-0 via shim `_python-hook.sh:409-413` | ORACLE de regressão sobre hooks WIRED (T2) | Fecha a classe "exit-2 acidental" como guard de regressão, sem quebrar contratos CLI |
| G5 | Subagentes **async por default** (2.1.198) + caps nativos: 20 concorrentes (2.1.217), 200/sessão (2.1.212), nesting depth 3 (2.1.219, flip-flop) | Rail 2 depth-fence EXISTE (`check_agent_spawn.py:1822-1833`) mas advisory + sinais COOPERATIVOS; cobertura em depth≥2 DESCONHECIDA | ADOPT+VERIFY (T4, CF-3) | Doutrina async; possível cap de fan-out maior (decidido por medição); governança de nesting |
| G6 | Task tool `mode` ignorado (2.1.212) | Spawn guard não referencia mode (verificado round-1) | VERIFY leve (T2) | Assunção morta descartada com prova |
| G7 | Novos hook events: `Notification` (2.1.198) e `DirectoryAdded` (2.1.219) | Não wired (13 tipos atuais). `/add-dir` fora do projeto expõe `~/.claude/` (user-scope, fora do HMAC-audit). **Version-floor de adopters não resolvido** (SUPPORT.md `>=2.0`; tolerância a event-key desconhecido não provada) | ADOPT gated (T3, CF-9, codex F10/grok F9) | **Segurança** (perímetro) + observabilidade/liveness |
| G8 | Novas settings: `sandbox.network.strictAllowlist`, `sandbox.filesystem.disabled`, `workflowSizeGuideline`, `disableAutoMode`, rename `defaultMode: manual` | settings/templates sem as chaves | ADOPT seletivo (T5, OQ5) | Postura de governança + templates atualizados |
| G9 | MCP tool calls >2min auto-background (2.1.212) | Matchers `mcp__codex__*` wired; reviews codex 10-15min | VERIFY (T2.4) — registrar resultado mesmo se dormente | Pair-rail não muda de semântica em silêncio |
| G10 | `/code-review` roda como subagente background (2.1.218) | Pair-rail é subprocess CLI | DOC (T6) | Clareza de doutrina |
| G11 | Plugin shell-form `${user_config.*}` rejeitado (2.1.207) | Framework não usa plugins | SKIP (verificado) | n/a |
| G12 | Mudanças internas de custo no CLI (2.1.210/216/217 — normalização, transcript, tool rounds) | A base empírica do cap N≤6 (PLAN-083) foi medida no substrato antigo | RE-MEASURE (T4) — sem herdar números do changelog | Cap de fan-out re-fundamentado em medição própria |
| G13 | codex_cli 0.144.1→0.144.6 instalado; grok 0.2.93→0.2.106 instalado; grok sem PROBE de código | Semver pin já cobre 0.144.6; `codex-cli-binary-sha256.txt` atesta o LAUNCHER (`codex.js`, sha `134063e1…`) e o payload nativo real difere (`80a3933d…` — provado 2×); **enforcement em runtime é STUB** (`pair-rail-gate.sh:139-149` só semver; `check_pair_rail.py` não compara sha; só release.yml compara metadata) | FIX mecanismo + enforcement + cerimônia (T5) | Supply-chain do V2 vira CONTROLE, não label |
| G14 | Agent teams / SendMessage nativos | Zero uso | EVALUATE (OQ4) — draft: documentar postura | Governança de peer-messages não modelada |
| G15 | Fast mode Opus 5/4.8 ($10/$50) | Zero uso | DOC guidance (T6, OQ6) | Trade-off custo×latência documentado, decisão do operador |
| G16 | Workflow `opts.model` era INERTE (W0a, PLAN-134) | Workaround subprocess em eval-baseline-n20 | RE-VERIFY em 2.1.220 (T4.4) | Se consertado → simplificação (follow-up) |
| G17 | Agent SDK TS 0.3.198 / Py 0.2.110 last-seen 2026-07-01 | Ledger stale | REFRESH (T5.1) | Higiene do watch |

## Gates nomeados (pré-condições duras — ORDEM CORRIGIDA por codex F5/grok F3)

Ordem obrigatória: **GATE-PIN → GATE-V2 (sob o pin novo) → review do pack W3
→ cerimônia GPG do pack.**

- **GATE-PIN (CF-4):** cerimônia do pin codex (T5.2) PRIMEIRO — atestação
  payload-real + enforcement unstubbed. Liveness coletada sob o pin velho
  NÃO atesta o reviewer novo.
- **GATE-V2 (CF-8, endurecido por codex F3/grok F2; RE-ESCOPADO por
  stop-review S283):** NÃO basta o row `pair_rail` do
  `failopen_rail_liveness_7d` estar verde — zero-expected + zero-outcomes
  classifica GREEN vácuo (`ceo-boot.py:1902-1905`), e a expiração natural
  (≈2026-08-03) satisfaria sem prova. **Correção S283 (any-in-window):** a
  janela de avaliação do gate é **exclusivamente os eventos com timestamp
  POSTERIOR à cerimônia do pin** (âncora = ts do commit assinado do
  GATE-PIN), nunca a janela 168h inteira — senão (a) fail-opens antigos
  pré-pin bloqueariam o gate até 08-03 sem razão, e (b) após 08-03 a
  expiração satisfaria vacuosamente. Sobre o conjunto pós-pin o gate exige:
  ≥1 invocação fresca classe A-E com `expected >= 1`, outcome terminal,
  `healthy >= 1`, `failopen == 0`, sem missing/duplicate/coverage deficit.
  São **duas cerimônias** (pin + pack GPG), declaradas.

## Threads / Waves

### W0 — Debate + tie-breaks
Debate round-1 CONCLUÍDO (3×ADJUST→PROCEED, 14 ajustes). Review cross-vendor
CONCLUÍDO até APPROVE duplo (codex r5 + grok delta-confirm — ver Context).
**W0b CONCLUÍDO (S284, 2026-07-28):** OQs ratificadas pelo Owner via
AskUserQuestion estruturado — **OQ1=(b) refresh completo** (fallback →
opus-5 imediato, SEM soak); **OQ2=migrar advisory já** (sonnet-5 neste
pack, com a contingência T1.1 mantida: se o fail-open de
`enforceAvailableModels` confirmar, o default de sessão é pinado
explicitamente no MESMO commit); **OQ3=pin=1** + 4 probes;
**OQ4=documentar** postura; **OQ5=(c) expor + LIGAR dogfood**
(recomendação do crítico de segurança acatada); **OQ6=guidance**.
Literais materializados na tabela T5.4.
Check: none (gate de cerimônia).

### T1 — Model refresh Claude 5 (W2 mecânico + W3 canônico)
1. **Pré-passo (CF-6):** verificar no diff de schema do T2.2 a semântica de
   default-resolution de `enforceAvailableModels` no 2.1.220 (incl. o
   fail-open documentado de managed-policy). SE confirmada: a entrada
   `claude-sonnet-5` no working-set MIGRA para pós-baseline da OQ2, OU o
   default de sessão é pinado explicitamente no MESMO commit.
2. **Fonte de verdade (codex F6, corrigido em r2):** a mudança de frota é
   uma EMENDA ao ADR-149 — blocos `AVAILABLE_MODELS_WORKING_SET`
   (+= claude-opus-5; += sonnet-5 conforme item 1) e **`FALLBACK_MODEL_CHAIN`**
   (identificador exato, ADR-149:89-93; OQ1/b-soak). O generator
   (`generate-available-models.py:43-49,256-270`) parseia SÓ o working-set
   e o VETO floor e emite SÓ `availableModels` — portanto: (a) regen de
   `availableModels` via generator nos DOIS espelhos; (b) `fallbackModel`
   atualizado explicitamente nos DOIS espelhos (settings.json +
   settings.base.json) como passo próprio; (c)
   `test_available_models_mirror.py` verde (a igualdade do fallback é
   enforced em :193-200). Edits diretos de `availableModels` são PROIBIDOS.
   **(d) Espelhos INDEPENDENTES (codex r2 #7, contrato ADR-149:39-43):**
   `validate-governance.sh:707-723` e `tier_policy_cli/_types.py:26-34`
   ainda aceitam só os 4 ids antigos — inventariar e atualizar TODOS os
   validadores independentes exigidos pelo ADR-149, regenerar anchors
   congelados onde houver, e teste de paridade não-vácuo amarrando os ids
   aceitos ao working-set/floor do ADR. — **canônico/kernel** (W3).
3. ADR-149 VETO_FLOOR_ALLOWED += `claude-opus-5` (agent_frontmatter.py:136)
   — **kernel** (W3, OQ1). Fable-5 permanece o teto.
4. `model_routing.py:59-65`: debate/arch → `claude-opus-5`; advisory conforme
   OQ2; mapa role→model de `audit_log.py:890-917` idem (routing, não
   pricing — grok F11).
5. **Fix presence-based (CF-2, escopo corrigido por grok F11), ADITIVO:**
   (a) RED HOJE: `_PRICING_PER_MTOK` (audit-telemetry.py) += opus-4-8,
   fable-5 (+ opus-5/sonnet-5); detectors `_LARGE_MODELS`/wasteful +=
   fable-5, opus-5. (b) SÓ IDS NOVOS (já contêm opus-4-8/fable-5):
   `cost-table.yaml`, `ceo-cost.py`, `budget-summary.py` += opus-5 (+fast
   row), sonnet-5. NUNCA remover ids históricos (replay ADR-142).
   Display-map de `generate-dispatch.py` e docstrings de `context-budget.py`
   fora de escopo.
6. `team.md:578` E `:589`: drift textual (cache-stable: editar SÓ no
   closeout, junto do commit da cerimônia).
7. **Parity com assert real (codex F9):** `smoke-install-parity.sh` só
   valida frontmatter/env — adicionar asserção EXPLÍCITA de que
   `availableModels` instalado contém a frota nova (e ordem do fallback);
   ALLOWED_MODELS += opus-5/sonnet-5 continua, mas não é evidência sozinha.
8. **STALE_RE += `claude-opus-4-1` (CF-11 + grok F7):** born-green hoje
   (zero hits no repo) → plantar fixture negativa deliberada fora das
   allowlists para o red-first (padrão planted-fixture do FOLLOWUP), com os
   deltas de allowlist enumerados ANTES (`model-deprecations.json`,
   `check-model-deprecations.py`, `.claude/data/canonical_models.json`).
9. `model-deprecations.json`: refresh via recipe PENDING-OWNER.
10. ADR novo `ADR-181-claude-5-model-refresh`: sunset do opus-4-8 no floor
    (evento pós-migração, ADR-095) + nota do gap runtime-fallback vs
    bijeção de floor.
Check: oracle presence-based NASCE VERMELHO hoje (audit-telemetry sem
opus-4-8/fable-5) e fica verde no pack; mirror test verde após regen;
asserção de availableModels instalado verde; parity verde com STALE_RE
ampliado + fixture negativa provando o red path.

### T2 — Conformidade de hooks com o harness 2.1.220 (W1 red-first)
1. **Oracle `hook-stdout-schema-check` (retargetado por codex F2/grok F1;
   contrato corrigido por codex r2 #3):** conjunto = hooks WIRED derivados
   do settings.json em runtime (zero contagens hardcoded). CONTRATO REAL:
   o shim é `exec` puro (`_python-hook.sh:409-413`) — exit codes chegam ao
   harness inalterados; denies intencionais são **exit-0 + decision-JSON**
   consumidos pelo harness; sob 2.1.214 um exit-2 acidental BLOQUEIA (não
   há fail-open pelo caminho do shim). O oracle asserta: (a) fixtures de
   falha de INFRAESTRUTURA de cada hook wired emitem `{}` + exit 0;
   (b) falhas de INPUT dos matchers de segurança emitem block-JSON + exit 0
   (fail-closed por decisão, não por crash); (c) schema do stdout JSON nos
   dois caminhos; (d) check ESTÁTICO rejeitando `argparse`/`SystemExit` não
   tratados em qualquer hook wired (guard de regressão). Os 3 scripts
   argparse ficam FORA do escopo de hook-protocol: `check_harness_config.py`
   MANTÉM exit≠0 (contrato validate.yml:960-984); emit_architect_outcome/
   policy_dispatch são unwired/shadow (ADR-049) — higiene CLI apenas.
2. **Artefato de schema versionado (CF-5):** extração zod do binário 2.1.220
   commitada (JSON + stamp + sha256 + recipe). Oracle CI valida contra o
   snapshot (validate.yml não tem o binário); job próprio com
   `timeout-minutes` + entrada no pre-push. Diff 2.1.202→2.1.220 com
   disposição por campo nos 8 hooks schema-densos — incluindo re-verificação
   de `enforceAvailableModels` (alimenta T1.1) e da tolerância a event-keys
   desconhecidos (alimenta T3).
3. G9: probe do auto-background MCP >2min vs `mcp__codex__*` — registrar
   resultado mesmo se dormente.
4. G6: prova leve de independência de `mode`.
Check: oracle verde sobre o conjunto DERIVADO de hooks wired (schema +
exit-0 nos dois caminhos + check estático argparse/SystemExit) no CI e
pre-push; artefato de schema commitado com sha; diff por campo anexado em
`PLAN-163/`.

### T3 — Novos hook events (W3 canônico — cerimônia; template GATED)
1. **Probe de blockability = HARD GATE (CF-9/grok F6):** antes de qualquer
   promessa de enforcement, provar se `DirectoryAdded` aceita decisão de
   block. SE SIM: `check_directory_added.py` com hardblock-FLOOR
   **estreitado (grok F12)** — raiz de `$HOME`, `~/.claude/`, qualquer
   árvore `**/.claude/**` alheia — independente do env; ancestrais do
   project dir REMOVIDOS do floor (residual monorepo documentado + opção de
   allowlist do Owner); demais paths audit-only, deny opt-in
   `CEO_DIRADD_HARDBLOCK=1`; dogfood liga. SE notification-only (grok F6 +
   grok r2 F3): `DirectoryAdded` é wired MESMO ASSIM como
   **observer-WRITER** — `check_directory_added.py` grava o registry de
   roots-adicionados em `.claude/state/session-roots.json` (schema
   versionado, escopo por session_id, TTL = sessão; `.claude/state/` é
   non-commit/gitignored — política declarada); os CONSUMIDORES nomeados
   são os guards PreToolUse da família Edit|Write|MultiEdit (deny de
   escrita sob root registrado não-allowlisted), com matching por
   caminho ABSOLUTO + `realpath` (guards atuais são project-relative —
   extensão explícita), canonicalização fail-CLOSED em path não-parseável
   (matcher de segurança, CLAUDE.md §4), fixtures `TestEnvContext`. Sem o
   writer, o write-guard nasceria verde — o probe vermelho é a escrita sob
   root registrado ANTES do guard existir.
2. Wiring `Notification` (agent_needs_input/agent_completed) → audit-emit
   tipado com **no-value-echo**; alimenta telemetria de liveness.
3. **Registrations derivadas, não hardcoded (codex F7/grok F5):** dogfood
   46→**48**; template settings.base.json 45→**47** (exclusão intencional
   de check_cost_envelope preservada — `test_template_dogfood_parity.py`).
   Todos os oracles derivam a expectativa DO ARTEFATO SOB TESTE.
4. **Version-floor de adopters (codex F10/grok F9):** SUPPORT.md declara
   `>=2.0`; ANTES de emitir os eventos novos nos templates: probe de
   tolerância a event-key desconhecido numa versão-piso OU decisão
   explícita de subir o floor (SUPPORT/install/upgrade coerentes). Até lá,
   emissão nos templates é FEATURE-GATED (dogfood pode wired imediatamente).
5. ADR do T3: ativo protegido (`~/.claude/` fora do HMAC-audit), nota
   SlashCommand, residual monorepo do floor.
Check: probe live de blockability com resultado registrado; se blockable —
probe de root sensível BLOQUEADO; se não — write-guard bloqueia a escrita
sob root registrado; `hook_live_smoke` reconta a partir do settings.json
(48 dogfood); oracles de template derivam 47; probe de version-floor
registrado antes de template-emission.

### T4 — Paralelização & doutrina async (W1 medição + W2 doutrina)
1. **Re-medição do cap (CF-10):** protocolo PRÉ-REGISTRADO — ≥200 amostras
   por nível N∈{6,8,12} (classe PLAN-159), máquina local idle identificada,
   p50+p95 e threshold exatos, workload shape PLAN-083. Cap novo exige as
   **três** justificativas re-validadas (flock audit-log, git index lock,
   budget-guard tally) — OU cap maior escopado a fan-outs READ-ONLY
   mantendo 6 para staging. Edit da skill declara o rail de governança
   (SP-NNN + soak, ou scope do sentinel com justificativa).
2. **Doutrina async-subagent:** ADR curto — default async (2.1.198), caps
   nativos (20/200/depth-3), como cerimônias aguardam conclusão
   (SubagentStop), interação com o cap interno.
3. **Nesting depth (OQ3, CF-3):** draft pin
   `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`, Check com 4 probes red-first:
   (i) env var verbatim vs binário (classe S218); (ii) probe de NEGAÇÃO;
   (iii) hook-coverage em depth-2 (PreToolUse dispara para Task de
   subagente?); (iv) regressão dos 3 instrumentos Workflow sob o pin.
   Rail 2 depth-fence citado corretamente (advisory, sinais cooperativos).
4. G16: re-verificar Workflow `opts.model` no 2.1.220; se funcional →
   follow-up (fora deste plano).
Check: relatório em `PLAN-163/flock-2.1.220.md` com protocolo cumprido
(≥200/nível, p50/p95); decisão de cap citando os 3 fundamentos; 4 probes de
depth registrados; env pin (ou re-escopo justificado) no pack.

### T5 — Ledger, pins e templates (cerimônia do pin própria + W2)
1. `substrate-watch.json`: claude_code → 2.1.220, agent_sdk_ts/py (fetch —
   recipe PENDING-OWNER se rede gated), codex_cli/harness → 0.144.6,
   grok_cli → 0.2.106; **registrar probe de código do grok em
   `_PROBE_ARGV`** (`["grok", "--version"]`).
2. **Pin codex (CF-4; endurecido por codex F4/F12 + grok F4/F10; fechado
   end-to-end por codex r2 #4/#6 + grok r2 F1/F2):**
   (a) **Alvo real:** o launcher resolve o binário via PACOTE OPCIONAL DE
   PLATAFORMA — `@openai/codex-<platform>/vendor/<targetTriple>/bin/codex[.exe]`
   (medido darwin-arm64: `…/@openai/codex-darwin-arm64/vendor/
   aarch64-apple-darwin/bin/codex`, sha `80a3933d…`; `…/@openai/codex/vendor`
   NÃO existe). O algoritmo de resolução espelha o `findCodexExecutable`
   do launcher e vira helper versionado; hash de `$(which codex)`/launcher
   é CLASSE DE FALHA explícita na cerimônia.
   (b) **Schema do pin migra — CONTRATO DEFINIDO (codex r3 #1):**
   `codex-cli-binary-sha256.txt` hoje aceita UMA linha 64-hex — migrar para
   manifest versionado com serialização CONCRETA: JSON
   `{"schema": 1, "package_version": "<semver>", "npm_integrity": "<sri>",
   "payloads": {"<targetTriple>": {"path": "@openai/codex-<platform>/vendor/<targetTriple>/bin/codex[.exe]", "sha256": "<64-hex>"}}}`.
   Seleção de plataforma: o helper resolve o targetTriple corrente
   (espelhando o launcher) e indexa `payloads`; triple ausente = FALHA
   fail-closed. Representação no envelope do verdict: o campo escalar
   atual (`validate-pair-rail-verdict.py:338-380`) passa a carregar o
   sha256 DO PAYLOAD DA PLATAFORMA DO RUN + o targetTriple declarado —
   validator compara contra a entry correspondente do manifest. MIGRAR
   TODOS os consumidores enumerados: validator, template/envelope do
   verdict no release.yml, `pair-rail-gate.sh` Gate 4 (hoje só semver,
   :139-149), testes, E as seções de cerimônia/runtime de
   `docs/CROSS-LLM-THREAT-MODEL.md:349-356` (hoje documentam
   `shasum $(which codex)` — obsoleto).
   (c) **Enforcement no RAIL VIVO (mandatório): verify-then-invoke o MESMO
   path.** `_resolve_codex_bin` (`check_pair_rail.py:312-325`) passa a
   resolver o payload nativo, comparar o sha contra o manifest ANTES do
   subprocess (bloqueante em mismatch) e RETORNAR o executável verificado;
   `_invoke_codex_review` (:545-557) invoca EXATAMENTE esse path retornado
   (`cmd = [verified_native_path]`) — eliminando o gap
   verifica-A-executa-B (alternativa aceitável: atestar launcher E payload
   com design equivalentemente vinculante, decisão registrada no ADR novo).
   Preflight manual não é suficiente (não é wired; residual T-8 de swap
   mid-session). Teste que FALHA se o pin casar com `codex.js` e PASSA se
   casar com o payload; release metadata-compare NÃO conta como atestação
   de invoke.
   (d) **Registro decisório (codex r2 #6 + grok r2 F2):** **ADR-120 é o
   ADR de PII** — a cadeia "ADR-111 SUPERSEDED por ADR-120" no frontmatter
   é inconsistência de ledger (locked-corpus MANTEVE o id 111, ADR-117 /
   adr/README). Decisão do plano: **ADR NOVO** que passa a possuir
   payload-pin + enforcement em runtime, supersedendo EXPLICITAMENTE as
   seções de pin do registro locked-corpus, + REPARO do frontmatter/índice
   do ADR-111 (remover a relação falsa com ADR-120). NUNCA emendar
   ADR-120-pii.
   (e) Cerimônia assinada do pin PRIMEIRO (GATE-PIN), depois re-record
   fixtures PLAN-155 W1 → checklist ADR-161 → eleição catch_rate → GATE-V2
   fresco sob o pin novo.
3. Settings/templates: `defaultMode: "manual"`; expor comentado
   `workflowSizeGuideline`, `sandbox.network.strictAllowlist`,
   `sandbox.filesystem.disabled`, `disableAutoMode` (OQ5).
4. **Migração de upgrade BASELINE-AWARE (codex F8/r2 #5; chaves-folha
   enumeradas por r3 #2):** `upgrade.sh` só merge 5 lifecycle events e
   preserva settings do usuário — adopters NÃO receberiam frota/eventos
   novos. Migração explícita e IDEMPOTENTE, política 3-estados POR
   CHAVE-FOLHA — tabela normativa (baseline velho → novo):
   Regra normativa de ordem: ids NOVOS são APENDADOS AO FIM (a ordem é
   byte-comparada — ADR-149:95-102, mirror test :127-149,193-200 — e a 1ª
   entrada participa da resolução de default, T1.1); qualquer outra ordem
   exige justificativa no ADR-181. Arrays literais pós-W0b por opção:
   | Chave-folha | Baseline velho (literal) | Baseline novo (literal, por opção OQ1) |
   |---|---|---|
   | `availableModels` | `["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5"]` | **RATIFICADO (OQ1=b, OQ2=migrar-já):** `["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5","claude-opus-5","claude-sonnet-5"]` — sonnet-5 apendado NESTE pack, condicionado à resolução da contingência T1.1 no mesmo commit (pin explícito de default de sessão se o fail-open confirmar) |
   | `fallbackModel` (ORDEM inclusa) | `["claude-opus-4-8"]` | **RATIFICADO (OQ1=b):** `["claude-opus-5"]` |
   | `permissions.defaultMode` (contrato exato: `effective_config.py:178-180,534-542`) | `"default"` | `"manual"` (todas as opções) |
   | registrations novas (`DirectoryAdded`, `Notification`) | ausentes | entries canônicas (gated T3.4) |
   W0b MATERIALIZA na tabela os literais da opção escolhida ANTES de
   qualquer implementação de migração ou fixture (os fixtures byte-comparam
   os arrays escolhidos, nunca "+=").
   Ações por estado: (i) AUSENTE → escreve baseline novo; (ii) IGUAL ao
   baseline velho → atualiza; (iii) CUSTOMIZADO → PRESERVA + WARN nomeado.
   Registrations de hooks CUSTOMIZADAS não-relacionadas são preservadas ao
   adicionar as canônicas. Cada chave×ramo ganha fixture + oracle
   (incluindo o ramo AUSENTE e um fixture de estado MISTO) + oracle de
   idempotência (rodar 2× = mesmo resultado). O oracle de upgrade NÃO
   exige valor novo incondicional (contradiria a preservação).
5. **Oracles smoke-install (CF-7, corrigido; baseline-aware por r2 #5):**
   padrão U1-U3 — pós-install: availableModels contém a frota nova,
   defaultMode="manual"; pós-upgrade: asserções POR RAMO da migração
   (baseline→novo; customizado→preservado+WARN); registrations = valor
   DERIVADO do artefato (47 template / 48 dogfood).
Check: `check-substrate-watch.py --check` exit 0; pin-range test verde após
re-record; teste launcher≠payload verde (pin novo NÃO casa com codex.js);
Gate 4 do pair-rail-gate compara sha de verdade; oracles U4+ verdes com
expectativas derivadas; migração de upgrade provada em fixture.

### T6 — Docs & counts (W4 closeout)
1. Novo doc datado `docs/substrate-adopt-2026-08.md` com o diff de schema e
   decisões; CEO-MODEL-ROUTING.md, ACCELERATORS.md (fast-mode guidance como
   trade-off custo×latência, OQ6), doutrina G10; **nota tokenizer**:
   re-baseline de budgets shipped é follow-up plan.
2. **OUT-OF-SCOPE explícito:** job `opus-4-7-profiler-smoke`
   (validate.yml:1178) e `profile-opus-4-7.py` NÃO são renomeados
   (required checks de branch protection acoplam ao nome; rename é
   follow-up coordenado).
3. `verify-counts.sh` + `check-claude-md-claims.py` + regen
   COMMAND-SKILL-HOOK-MAP; sweep também nos docs não-vigiados
   (ARCHITECTURE/GUIA-COMPLETO/FAQ/npm-README).
4. **CLAUDE.md counts no closeout — TRIPLA completa (codex F11/grok F8):**
   hooks on disk 55→57, **wired 44→46**, registrations 46→48 (dogfood);
   superfícies de badge/README derivadas do disco. (cache discipline: só no
   closeout.)
Check: Validate GREEN no closeout; verify-counts sem drift, incluindo docs
não-vigiados e a tripla de counts.

## Addendum pós-review — findings do stop-review S283 (incorporados S284)

Quatro findings do stop-review cross-model da S283 sobre o texto reviewed,
incorporados ANTES da execução (fonte: handoff S283→S284):

1. **GATE-V2 any-in-window / expiração-vacuosa** — RESOLVIDO acima: a
   prova do gate é escopada a eventos PÓS-cerimônia-do-pin (âncora = ts do
   commit assinado), não à janela 168h.
2. **CF-9 fallback é só-ESCRITA** — no ramo notification-only do T3.1, o
   observer-writer + write-guard cobre apenas Edit|Write|MultiEdit sob
   root registrado. **LEITURA sob root adicionado (Read/Grep/Glob de
   `~/.claude/` alheio) permanece descoberta** — registrar como residual
   NOMEADO no ADR do T3 com disposição explícita (extensão de read-guard é
   follow-up; não silenciar).
3. **DirectoryAdded é PÓS-facto** — o evento dispara DEPOIS do root já
   adicionado; mesmo no ramo blockable, pode existir janela entre a adição
   e a decisão de block (reads podem ocorrer antes do deny). O probe do
   T3.1 DEVE medir e registrar essa janela (o block remove o root ou só
   impede uso futuro?); o ADR do T3 documenta a semântica pós-facto como
   limite do controle, e o floor/deny não pode ser vendido como prevenção
   total de exposição.
4. **Speed multipliers** — scrub de conformidade: nenhuma superfície deste
   plano (incl. guidance de fast-mode do T6/OQ6 e doutrina async do T4)
   pode citar multiplicadores/números de velocidade do CHANGELOG como
   benefício do framework (AGENTS.md no-speed-claim). Fast-mode guidance é
   trade-off custo×latência SEM números herdados; T6 ganha check de scrub
   (grep por padrões `[0-9]+(\.[0-9]+)?x|faster|speedup` nas superfícies
   tocadas).

## Open questions — RATIFICADAS pelo Owner em S284 (W0b fechado; ver W0)

- **OQ1 → (b) refresh completo** (Owner, S284): working-set + VETO floor +
  routing debate/arch → opus-5 E `FALLBACK_MODEL_CHAIN` → `claude-opus-5`
  imediato, sem janela de soak. (Draft era b-soak; Owner escolheu b.)
- **OQ2 → migrar advisory JÁ** (Owner, S284): advisory roles →
  claude-sonnet-5 neste pack, aceitando o risco tokenizer +30% sem
  re-baseline prévio (re-baseline `count_tokens` vira item do pack, não
  pré-condição). Contingência T1.1 MANTIDA como pré-condição técnica: se o
  fail-open de `enforceAvailableModels` confirmar, pin explícito do default
  de sessão no MESMO commit.
- **OQ3 → pin=1** com 4 probes red-first (draft acatado).
- **OQ4 → documentar** postura "não adotado — governança de peer-messages
  não modelada" (draft acatado).
- **OQ5 → (c) expor + LIGAR neste repo** (Owner acatou a recomendação do
  crítico de segurança): templates ganham as chaves comentadas E o dogfood
  liga postura fail-closed (`sandbox.network.strictAllowlist`,
  `sandbox.filesystem.disabled` avaliada contra os fluxos reais,
  `disableAutoMode`, `defaultMode: "manual"`, `workflowSizeGuideline`).
  Rollback documentado no pack.
  > **Nota (2026-08-02, PLAN-165):** a postura default acima segue
  > INALTERADA — tracked settings e templates continuam fail-closed.
  > O PLAN-165 adicionou apenas um override efêmero per-machine
  > (`/night-mode` → `permissions.defaultMode: "acceptEdits"` no
  > `.claude/settings.local.json` gitignored, snapshot/restore no `off`),
  > sem tocar a decisão do OQ5(c). Ver ADR-185.
- **OQ6 → guidance** no ACCELERATORS.md (trade-off custo×latência, Opus
  5/4.8 only, sem números de velocidade — ver Addendum item 4).

## Success criteria

- [x] G1-G17 com disposição executada ou registrada (evidência por item).
- [x] Gates honrados NA ORDEM CORRIGIDA: GATE-PIN → GATE-V2 (fresco, sob pin
  novo, healthy≥1 ∧ failopen==0 ∧ expected≥1) → review do pack → cerimônia
  GPG do pack.
- [x] Oracle `hook-stdout-schema-check` verde (conjunto WIRED derivado;
  schema + exit-0 nos caminhos allow/block + check estático
  argparse/SystemExit) no CI e pre-push; artefato de schema 2.1.220
  commitado; contratos CLI (check_harness_config exit≠0) intactos.
- [x] Oracle presence-based nasceu vermelho e ficou verde; mirror test do
  ADR-149 verde pós-regen; asserção de availableModels instalado verde;
  STALE_RE com fixture negativa provando red path.
- [x] Medição flock/index-lock/tally 2.1.220 commitada; cap decidido pelos
  números e escopo.
- [x] 4 probes de depth registrados; pin (ou re-escopo) aplicado.
- [x] `check-substrate-watch.py --check` exit 0; teste launcher≠payload
  verde; compare de sha BLOQUEANTE no rail vivo (`check_pair_rail.py`) +
  Gate 4 unstubbed; ADR novo do pin landado + ledger do ADR-111 reparado
  (relação falsa com ADR-120-pii removida).
- [x] Oracles smoke-install com expectativas DERIVADAS (47/48) verdes
  pós-install e pós-upgrade; migração idempotente de upgrade provada.
- [x] Probe de version-floor/unknown-event registrado antes de emitir
  eventos novos em templates.
- [x] Edits canônicos/kernel via staged pack + pair-rail APPROVE + cerimônia
  GPG (padrão PLAN-160/161); CLAUDE.md tripla de counts no closeout.
- [x] Validate GREEN no closeout; plano → done com related_commits.
  **(Validate success em `1241795`, 2026-07-30; done neste commit.)**

## Progress log

- **2026-07-30 (S286): PLANO DONE.** Sequência completa do Passo 4: W2
  live fixes commitados (`9477bde` — 2 P2 do codex resolvidos: pricing
  event-date-aware + opus-4-8-fast; Validate GREEN) → cerimônia do
  main-pack Owner-run (`8ed9f6f` `[SENT-PLAN163-PACK]`, GPG verified) →
  closeout de docs (`3bce87c` — tripla 57/46/48 + ADRs 184, riders
  team.md :578/:589, regen MAP, sweep de 6 docs; claims + verify-counts
  PASS) → red pós-pack corrigido (`1241795` — golden audit-registry
  +2 actions T3, exec bit em 3 hooks wired, TestEnvContext nas 2 classes
  bare do teste de migração; 94/94 local) → **Validate GREEN em
  `1241795`**. L-proof pós-land: smoke-install-parity PASS na árvore
  landada. Pré-requisito honrado: GATE-V2 PASS fresco sob âncora
  PLAN-164 (`PLAN-163/probes/GATE-V2-2026-07-30-PASS.md`).
- **2026-07-29 (S285):** GATE-PIN landado pelo Owner (`a4371c7`,
  `[SENT-PLAN163-PIN]`) + closeout do pin executado (ADR count 181 em 7
  superfícies, claims + verify-counts PASS, anchor tracked; `7860d62`,
  Validate GREEN). **GATE-V2 = FAIL**: probe fresco S281-pattern emitiu
  `case F / codex TIMEOUT` aos 30 s exatos; root cause MEDIDO = default
  `CEO_PAIR_RAIL_TIMEOUT_S=30` < 36,3 s reais de um verdito codex (12/12
  cases da história do log são F/TIMEOUT — o rail nunca completou review
  vivo; o pin corrigiu integridade, não latência). Evidência:
  `PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md` (`e540cd9`).
  **Owner ratificou opção C (tie-break S285): incidente formal do rail,
  pack ADIADO** até o fix durável + re-âncora via **PLAN-164** (draft).
- **2026-07-29 (S285, codex review dos W2 vivos):** 2 P2 ABERTOS a resolver
  ANTES do commit W2 da cerimônia do pack: (a) pricing Sonnet 5 estático
  não atravessa o cutoff 2026-08-31 — `_compute_event_cost_usd` ignora o
  ts do evento; design duplicado em `audit-telemetry.py` + `ceo-cost.py` +
  `budget-summary.py` (fix = pricing event-date-aware, não mutação da
  linha global); (b) falta a linha `claude-opus-4-8-fast` nas 4
  superfícies de pricing + fleet oracle (id válido em
  `canonical_models.json` / `model-deprecations.json` → hoje reporta
  custo zero/unknown). 3º finding (estado review-loop commitável)
  RESOLVIDO no ato via `.gitignore` (`.claude/state/review-loop/`).

## Blockers

- **Leaf:** PLAN-164 (timeout uplift + re-âncora) precisa chegar a `done`
  — o case-F pós-âncora tornou `failopen==0` insatisfazível contra a
  âncora `a4371c7`; o GATE-V2 só é satisfazível sob âncora nova. Cerimônia
  do pack (Passo 4 do runbook) proibida até GATE-V2 PASS.
- **Next (deste plano):** após PLAN-164 W3, retomar CEREMONY-RUNBOOK.md
  Passo 4 com `--confirm-gate-pin-done --confirm-gate-v2-fresh`.
