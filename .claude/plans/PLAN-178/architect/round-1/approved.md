---
plan: PLAN-178
round: 1
type: architect-sentinel
segment: LOTE-B-SPAWN-CONTRACT-V2
---

# PLAN-178 Lote B — spawn acceptance contract v2 (Owner sentinel)

Anchor-SHA: 451b6590279d47dbefa43d1d9ebced503c636e86

Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
Approved-At: 2026-08-16

## What this sentinel authorizes (sign this KNOWINGLY)

Single declared PLAN-178 Lote B ceremony (plan `executing`; RUNBOOK staged
S305 com manifesto rastreado verificado fail-closed; as 3 decisões ⚖️
ratificadas pelo Owner na S307 via AskUserQuestion: degradação POR
DIMENSÃO / gramática REDUZIDA p/ workflow-agents / check_budget NO PACK).
Um commit, um pack de 30 arquivos (+3.047/−237):

1. **C1 — FILE ASSIGNMENT grammar** (`check_agent_spawn.py`): classifier
   de 4 estados (absent/concrete/readonly/unparseable) com agregação de
   TODOS os blocos; token `CAN edit: NONE-READ-ONLY`; gramática de path
   concreto FECHADA (sem globs `*?[]{}<>`, sem whitespace Unicode, sem
   `$`, sem control chars/separadores de linha, ≤64 paths; violação
   MACULA a declaração inteira); parsing CommonMark-correto local
   (headers case-insensitive indent 0-3; fences coluna-0/indentados com
   tipo+comprimento de closer; comentário HTML não-fechado → EOF);
   whitelist FECHADA de linhas de lista com regra de sufixo por
   palavras de autoridade (token inteiro — filenames não contam); emit
   `spawn_file_assignment_recorded` em TODO spawn nomeado que DESPACHA
   (`path_count=0` na omissão/readonly/tainted — cura R-SEC1; sem
   reserva fantasma para spawn bloqueado); overlap roda também sobre
   paths de declaração tainted; enforce SÓ sob
   `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1` (NÃO armado — measure-first;
   janela conta would-block EXCLUINDO o marcador read-only); rota de
   recuperação `CEO_SOTA_DISABLE=1` TESTADA; 2 reason codes novos.
2. **C1 — gerador** (`inject-agent-context.sh`): `--files=<a,b>` →
   linhas `CAN edit:` (printf, nunca echo); sem arg → forma read-only
   explícita; validação ESPELHA a gramática do hook fail-closed
   (control chars via tr+igualdade, separadores Unicode NEL/LS/PS,
   whitespace via isspace(), globs, `$`, placeholders, token reservado,
   normaliza-vazio, cap 64) — o caminho canônico nunca emite prompt que
   o hook rejeitaria.
3. **C2 + validador pré-despacho — 4 workflows** (`audit-fanout.js`,
   `nightly-hygiene.js`, `council-audit.js`, `eval-baseline-n20.js`):
   bloco COMMON byte-idêntico (PROMPT_DEFENSE 6 bullets +
   FILE_ASSIGNMENT + fenceUntrusted cap 24000 anti-spoof com labels
   sanitizados + assertDispatchable com fences mascarados, max-
   semantics e taint de valores); TODO `agent()` embrulhado; variantes
   por-arquivo p/ transportes autorizados (council external:
   ADR-114-redacted brief; eval: seed→scratch→claude -p local);
   truncamento envenena POR DIMENSÃO (⚖️1) com severidade MONOTÔNICA e
   notices incondicionais apontando os campos estruturados retidos
   (audit-fanout devolve refuted/unverifiable completos); eval-recon
   truncado usa derivação MECÂNICA; council: verify truncado nunca
   CLEAN, lane reasons fenced; nightly ganha a dimensão (ix)
   `shared-memory-reopen` — o CONSUMER que torna o gatilho SEC-P0-02
   disparável (fontes: log canônico + rotações por stem + fallback +
   spools ativos/draining; count-only; red monotônico).
4. **C6 — fence no `memory_shared.query()`** (`_lib` canônico):
   `fence_untrusted_content()` com marcadores anti-spoof (escapados no
   corpo); storage byte-idêntico; SEM campo de corpo cru no resultado
   (decisão que fecha a oscilação codex r4↔r7: hash verification lê o
   arquivo em `_patterns_dir()`); `session_id` no emit_pattern_stored
   (torna o gatilho derivável); teste guarded em
   `_lib/tests/test_memory_shared_fence.py` POR DESIGN.
5. **check_budget — cura do cap INERTE** (⚖️3): ≥2 planos ativos
   deixa de ser skip; tie-break determinístico (executing>reviewed>
   draft → maior NNN → filename); base de gasto DECLARADA no warning
   (project-wide até o producer emitir plan_id — destino registrado);
   eventos por-plano suprimidos no multi-plan (breadcrumb forense; enum
   do schema intocado); `strict_attribution` testado como contrato
   futuro.
6. **ADR-191** (spawn acceptance contract v2, com R-SEC4/R-SEC5/R-SEC6/
   R-CAL1 declarados) + **ADR-089-AMEND-1** (`amends: ADR-089`; gatilho
   derivável count-only + fence; desvio do SPEC registrado com destino
   v1.4.0) — ACCEPTED.
7. **Derivadas no mesmo commit:** env-inventory regen (496 vars — cura
   28 drifts pré-existentes + 1 novo); contagens ADR 190→192 em 9
   superfícies + lib_recursive 140→141 (verify-counts exit 0);
   CLAUDE.md §4 (claim do spawn reescrita p/ o estado REAL pós-pack) e
   §5 (rail Workflow: aberto→MITIGADO); template do `team.md` fala a
   gramática nova; `spawn.md`/`architect.md` instruem `--files=` e os
   5+1 arquivos reais do bundle; e2e hook-chain 2→3 linhas; registro de
   execução no PLAN-178 (AC-7 fechado).

**O que este pack NÃO faz (sign this too):** NENHUM flip C5
(`CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED`/`CEO_SPAWN_OVERLAP_GUARD`
desarmados — flip é cerimônia FUTURA gated na janela advisory ≥30d/≥20
sessões com tabela would-block/TP-FP); NENHUMA linha de PROTOCOL.md;
NENHUM write-time enforcement (ADR-191 §2.6); NENHUMA edição de SPEC/v1
(deny-Edit — desvios registrados com destino). Residuais ASSINADOS
conscientemente: R-SEC4 (fence é moldura, não autoridade), R-SEC5
(markdown flat: exemplos devem ir em fence), R-SEC6 (parser = subconjunto
documentado de CommonMark; variantes além dele = extensão do residual;
cura estrutural exigiria lib de Markdown, vetada por stdlib-only),
R-CAL1 (emit advisory pode sobre-contar would-block quando gate
posterior veta — direção conservadora; flip filtra por veto_triggered).

**Gates executados ANTES deste pedido de assinatura:** rail codex
**44 rodadas** (~60 achados curados; 2 oscilações fechadas por DECISÃO
registrada em ADR; limpos em r21/r36/r43 e **r43+r44 = 2 GOs
consecutivos sobre o estado final**; vereditos arquivados em
`staged-loteB/codex_loteB_r*.md`); suíte completa no clone
`git clone --local` 12.589 passed/0 failed (exit verdadeiro); dirigida
final 110+; `node --check` 4/4 + smoke de EXECUÇÃO dos 4 workflows com
stubs 4/4 (pegou o TDZ do r24); prova funcional do validador 18/18;
`verify-counts` exit 0; `check-claude-md-claims` exit 0; env-inventory
`--check` exit 0; adr-chain: 11 erros PRÉ-existentes idênticos no repo
real, zero nos ADRs novos; positive controls live do gerador (hífen ✓,
newline ✗, NEL/LS/PS ✗, U+00A0 ✗, POSIXLY_CORRECT ✓).

Ceremony inputs integrity-pinned: manifesto RASTREADO
`.claude/plans/PLAN-178/staged-loteB/MANIFEST-loteB.sha256` cobre
RUNBOOK + drafts + `loteB-pack.patch` + vereditos r1-r44;
`shasum -a 256 -c` roda fail-closed ANTES do apply.

Commit subject tag: `[SENT-PLAN178-LOTEB]`.

## Scope

Scope:

Canonical (hooks + _lib + workflows + gerador + templates + ADRs):
  - .claude/adr/ADR-089-AMEND-1-shared-memory-reopen-trigger-and-query-fence.md
  - .claude/adr/ADR-191-spawn-acceptance-contract-v2.md
  - .claude/commands/architect.md
  - .claude/commands/spawn.md
  - .claude/hooks/_lib/memory_shared.py
  - .claude/hooks/_lib/tests/test_memory_shared_fence.py
  - .claude/hooks/check_agent_spawn.py
  - .claude/hooks/check_budget.py
  - .claude/scripts/inject-agent-context.sh
  - .claude/team.md
  - .claude/workflows/audit-fanout.js
  - .claude/workflows/council-audit.js
  - .claude/workflows/eval-baseline-n20.js
  - .claude/workflows/nightly-hygiene.js
  - CLAUDE.md

Free surfaces in the SAME commit (tests + derived counts + plan record):
  - .claude/hooks/tests/test_check_agent_spawn_file_assignment.py
  - .claude/hooks/tests/test_check_budget.py
  - .claude/hooks/tests/test_e2e_hook_chain.py
  - .claude/hooks/tests/test_memory_shared.py
  - .claude/plans/PLAN-178-mast-audit-substrate-adoption.md
  - .claude/plans/PLAN-178/architect/round-1/approved.md
  - .claude/plans/PLAN-178/architect/round-1/approved.md.asc
  - .claude/plans/PLAN-178/staged-loteB/MANIFEST-loteB.sha256
  - .claude/plans/PLAN-178/staged-loteB/loteB-pack.patch
  - .claude/plans/PLAN-178/staged-loteB/codex_loteB_r1.md ... r44.md (44 vereditos)
  - .claude/plans/PLAN-178/staged-loteB/approved-draft.md
  - .claude/plans/PLAN-178/staged-loteB/test-validator.js
  - .claude/scripts/env-inventory.json
  - CHANGELOG.md
  - README.md
  - README.pt-BR.md
  - docs/ARCHITECTURE.md
  - docs/CTO-GUIDE.md
  - docs/FAQ.md
  - docs/GUIA-COMPLETO.md
  - docs/README.md
  - npm/README.md
