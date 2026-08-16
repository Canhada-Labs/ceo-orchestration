---
plan: PLAN-178
round: 1
type: architect-sentinel
segment: LOTE-B-SPAWN-CONTRACT-V2
---

# PLAN-178 Lote B — spawn acceptance contract v2 (Owner sentinel)

Anchor-SHA: __ANCHOR_SHA__

Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
Approved-At: 2026-08-14

## What this sentinel authorizes (sign this KNOWINGLY)

Single declared PLAN-178 Lote B ceremony (plan `executing`; debate r1 do
plano fixou a estrutura do W-C; RUNBOOK staged S305 com manifesto
rastreado verificado fail-closed; as 3 decisões ⚖️ ratificadas pelo
Owner na S307 via AskUserQuestion: degradação POR DIMENSÃO / gramática
REDUZIDA / check_budget NO PACK). Um commit, um pack:

1. **C1 — FILE ASSIGNMENT grammar** (`check_agent_spawn.py`):
   classifier de 4 estados (absent/concrete/readonly/unparseable);
   token novo `CAN edit: NONE-READ-ONLY` (case-insensitive; nunca vira
   path de overlap); `none` PERMANECE placeholder dropado; emit
   `spawn_file_assignment_recorded` em TODO spawn nomeado
   (`path_count=0` em absent/readonly/unparseable — cura R-SEC1;
   readonly grava o hash constante do token como discriminador,
   allowlist intacta); enforce SÓ sob
   `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1` (NÃO armado neste pack —
   measure-first); rota de recuperação `CEO_SOTA_DISABLE=1` TESTADA;
   2 reason codes novos mapeados em `_BLOCK_REASON_MARKERS`.
2. **C1 — gerador** (`inject-agent-context.sh`): `--files=<a,b>` →
   linhas `CAN edit:`; sem arg → forma read-only explícita; bloco
   emitido SEMPRE (censo: o gerador era o maior omissor).
3. **C2 + validador pré-despacho — 4 workflows** (`audit-fanout.js`,
   `nightly-hygiene.js`, `council-audit.js`, `eval-baseline-n20.js`):
   bloco COMMON byte-idêntico (PROMPT_DEFENSE 6 bullets +
   FILE_ASSIGNMENT + fenceUntrusted cap 24000 + assertDispatchable);
   TODO `agent()` embrulhado (censo mecânico: 0 call sites nus);
   truncamento envenena POR DIMENSÃO (audit-fanout: degradedFinders;
   nightly: piso mecânico green→yellow; eval-recon: anomaly
   obrigatória; sites de síntese com veredito mecânico por contagens:
   degrada só o relatório, documentado inline).
4. **C6 — fence no `memory_shared.query()`** (`_lib` canônico):
   `fence_untrusted_content()` puro no retorno; storage byte-idêntico
   (teste prova); teste guarded em `_lib/tests/test_memory_shared_fence.py`
   POR DESIGN (des-fenciar exige cerimônia).
5. **check_budget — cura do cap INERTE** (Decisão 3): ≥2 planos ativos
   deixa de ser skip; tie-break determinístico (executing>reviewed>
   draft, depois maior NNN por filename, nunca mtime); breadcrumb
   nomeia a seleção; 3 testes do skip antigo CONVERTIDOS (não
   deletados) + 3 novos.
6. **ADR-191** (spawn acceptance contract v2) + **ADR-089-AMEND-1**
   (gatilho derivável p/ SEC-P0-02 + fence no query()) — ACCEPTED.
7. **Derivadas no mesmo commit:** env-inventory regen (496 vars — cura
   28 drifts pré-existentes + 1 novo `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED`);
   contagens ADR 190→192 em 9 superfícies (verify-counts exit 0);
   `docs/ARCHITECTURE.md` lib_recursive 140→141 (teste novo em _lib);
   teste e2e hook-chain 2→3 linhas (o evento novo é o comportamento
   correto); registro de execução no PLAN-178 (AC-7 fechado).

**O que este pack NÃO faz (sign this too):** NENHUM flip C5
(`CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED` / `CEO_SPAWN_OVERLAP_GUARD`
seguem desarmados — flip é cerimônia FUTURA gated na janela advisory
≥30d/≥20 sessões com tabela would-block/TP-FP); NENHUMA linha de
PROTOCOL.md (W2.1 não ratificada); NENHUM write-time enforcement
(declarado não-construível, ADR-191 §2.6). Positive controls live-fire
dos 3 fences rodam PÓS-land (AC-6).

Gates locais executados ANTES deste pedido de assinatura: suíte
completa no clone `git clone --local` (12.575 passed / 1 red curado no
próprio teste que pinava a cegueira antiga → 5/5 + 200/200 dirigidos);
`node --check` 4/4; prova funcional do validador 10/10 (inclui
byte-igualdade do COMMON nos 4 arquivos); `verify-counts` exit 0;
`check-claude-md-claims` exit 0; env-inventory `--check` exit 0; rodada
codex sobre o pack: __CODEX_RESULT__.

Ceremony inputs integrity-pinned: manifesto RASTREADO
`.claude/plans/PLAN-178/staged-loteB/MANIFEST-loteB.sha256` cobre
RUNBOOK + drafts + `loteB-pack.patch`; `shasum -a 256 -c` roda
fail-closed ANTES do apply.

Commit subject tag: `[SENT-PLAN178-LOTEB]`.

## Scope

Scope:

Canonical (hooks + _lib + workflows + gerador + ADRs):
  - .claude/adr/ADR-089-AMEND-1-shared-memory-reopen-trigger-and-query-fence.md
  - .claude/adr/ADR-191-spawn-acceptance-contract-v2.md
  - .claude/hooks/_lib/memory_shared.py
  - .claude/hooks/_lib/tests/test_memory_shared_fence.py
  - .claude/hooks/check_agent_spawn.py
  - .claude/hooks/check_budget.py
  - .claude/scripts/inject-agent-context.sh
  - .claude/workflows/audit-fanout.js
  - .claude/workflows/council-audit.js
  - .claude/workflows/eval-baseline-n20.js
  - .claude/workflows/nightly-hygiene.js

Free surfaces in the SAME commit (tests + derived counts + plan record):
  - .claude/hooks/tests/test_check_agent_spawn_file_assignment.py
  - .claude/hooks/tests/test_check_budget.py
  - .claude/hooks/tests/test_e2e_hook_chain.py
  - .claude/hooks/tests/test_memory_shared.py
  - .claude/plans/PLAN-178-mast-audit-substrate-adoption.md
  - .claude/plans/PLAN-178/staged-loteB/MANIFEST-loteB.sha256
  - .claude/plans/PLAN-178/staged-loteB/loteB-pack.patch
  - .claude/scripts/env-inventory.json
  - CHANGELOG.md
  - CLAUDE.md
  - README.md
  - README.pt-BR.md
  - docs/ARCHITECTURE.md
  - docs/CTO-GUIDE.md
  - docs/FAQ.md
  - docs/GUIA-COMPLETO.md
  - docs/README.md
  - npm/README.md
