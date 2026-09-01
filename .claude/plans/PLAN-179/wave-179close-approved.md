# wave-179close — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `PLAN-183/w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` —
> nunca escrito à mão. O `Anchor-SHA` é preenchido pelo
> `OWNER-S335-179CLOSE-SIGN.sh` com `git rev-parse HEAD` no momento da
> assinatura; o `OWNER-S335-179CLOSE-LAND.sh` aborta no G1 se não casar.
> Reescrever um byte deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-179
Wave: wave-179close (PLAN-179 — «Fechar tudo», ratificação do Owner de 2026-08-31: US7 = o snapshot do PreCompact vira ÍNDICE do ledger e o PostCompact rende o pointer ESTRUTURAL; US8 = SessionEnd ganha o rail stat-only de delta de memória implementado DA spec assinada, com a ação `session_memory_delta_observed` SPEC v2.60; US2b-valve = η advisory + doutrina do deny como limite de substrato; US1-veredito e AC(a) do W0 supersedidos pela r1-C3; e o flip `executing → done` do plano viaja NO patch, porque o done só é verdade no land)
Patch: .claude/plans/PLAN-179/s335-ceremony-179close/W179CLOSE.patch
Patch-sha256: 6714a0a48c56290a4fb5564e5b34b28b12a5867544b91ecb7918b0fba4aa14de
Patch-base: 4f6dda034b74bfef18329fef8fbd4e9a25e8e36d
Anchor-SHA: ANCHOR-PLACEHOLDER
Data: DATA-PLACEHOLDER

## O que esta wave entrega

**Cinco arquivos canônicos** e **treze não-canônicos** que só são verdadeiros
juntos. O oráculo `--is-canonical` responde `1` para
`.claude/hooks/check_precompact_continuity.py`,
`.claude/hooks/check_postcompact_reinject.py`, `.claude/hooks/SessionEnd.py`,
`.claude/hooks/_lib/audit_emit.py` e `SPEC/v1/audit-log.schema.md`; `0` para
os demais. O patch é atômico de propósito: a ação registrada no código sem a
linha do SPEC quebraria o registry checker; o golden sem a regeneração
quebraria o CI; os 4 pins de contagem (330→331) sem o registro da ação
nasceriam vermelhos; e um `status: done` sem os checkboxes fechados seria
claim falsa numa superfície de governança.

1. **`check_precompact_continuity.py`** (canônico, US7 + US2b-valve) —
   `_ledger_index()`: o plan é derivado dos PATHS do último commit
   (tie-break determinístico espelhado LITERALMENTE de
   `check_ledger_checkpoint.derive_scope` — contrato proíbe import
   hook-a-hook; NUNCA `resolve_plan_id`, emenda r1-C6, com teste AST
   escopado às duas funções novas), apontando `PLAN-NNN/LEDGER.md` +
   seções (≤5, clampadas, SÓ no scratchpad) + last-commit. E
   `_eta_advisory()`: η=(T−F−S)/T = 887‰ em aritmética INTEIRA das
   constantes MEDIDAS (`F+S=112638`, `T=998043`, w0-measurement.md §C/§E),
   duas linhas de stderr por compactação; «negar» é documentado como
   limite do substrato — o mesmo enquadramento honesto do US9c.
2. **`check_postcompact_reinject.py`** (canônico, US7) — o pointer
   ESTRUTURAL `Work ledger: <path> (last touched at <sha>)`. Títulos de
   seção são CONTEÚDO de arquivo e nunca entram no instruction stream
   (doutrina Codex R5 P1-1, a mesma do label de checkbox); `pointer_count`
   segue contando POINTERS ONLY dentro do clamp 0..9 existente.
3. **`SessionEnd.py`** (canônico, US8) — implementado A PARTIR da spec
   assinada `PLAN-179/staged-w24/SESSIONEND-NOTE.md`: observação
   STAT-ONLY (`st_mtime` vs âncora de início de sessão), âncora resolvida
   chain (oldest-in-window, HMAC com predecessor REAL) → terminal honesto
   (a perna state_file foi APOSENTADA no r5: os.replace reseta até o
   st_birthtime — nenhum artefato imutável; o valor do enum segue
   registrado no wire, nunca produzido),
   observação ANTES do cleanup do tool_lifecycle (§5 constraint #1), emit
   ANTES do `session_end` (§5 constraint #2), linha de ratificação do
   operador (a OMISSÃO vira visível: `memory delta ABSENT`), sanitização
   §6 dos basenames (drop, nunca truncar), kill-switch 3-estados
   `CEO_SESSION_MEMORY_DELTA`. O hook NUNCA escreve memória.
4. **`_lib/audit_emit.py`** (canônico, KERNEL) — ação
   `session_memory_delta_observed` em `_KNOWN_ACTIONS` (330→331), emitter
   tipado `emit_session_memory_delta_observed`, allowlist dedicada
   deny-by-default + enums fechados com coerção TYPE-strict (off-enum →
   `other`, NUNCA → `written`; bool/float → sentinela 0). DENIED no wire:
   basenames, corpos, o path absoluto do memory-dir e o slug do `$HOME`.
5. **`SPEC/v1/audit-log.schema.md`** (canônico, deny-Edit) — a linha da
   ação (v2.60) na tabela + a linha v2.60 no histórico de versões.

Não-canônicos que viajam juntos: o golden regenerado (`# count: 331`), o
`harness-noop-allowlist.txt` novo (rota gate-side ADR-160 §7 exigida pela
spec §3), a suíte nova `test_session_end_memory_delta.py` (24 testes = §7 da
spec + paridade de enums + os controles dos rails r1-r5 — NFKC-bypass,
âncora forjada/field-set/predecessor-real, compact-restart, perna
state_file APOSENTADA, scan incompleto, stat-final lento, preâmbulo de
papel, delta payload-gated), extensões em `test_check_compaction_continuity.py`
(14 testes US7/válvula/reinjector, incl. os controles de injeção do
título hostil e do shape do pointer — path/sha fora de forma caem), o rebaseline consciente dos 5 pins de contagem
(`test_audit_emit_api_contract.py` — contagem+SHA re-derivado+símbolo
público, `test_check_ledger_checkpoint.py`, `test_w5_scrub_enforcement.py`,
`test_codex_egress_proof_telemetry.py`,
`test_audit_emit_plan163_lifecycle_actions.py`,
`test_git_bypass_guard.py` — o 6º pin, achado pela bateria integral), o
plano com os 4 últimos
checkboxes fechados + AC(a) supersedido + registro S335 + frontmatter
`done`/`completed_at`/`related_commits`, o LEDGER com a unidade da
cerimônia, e o guia §2/§6 com as claims atualizadas (a claim «verifies
writability only» ficaria STALE sem isso).

## Kernel

`.claude/hooks/_lib/audit_emit.py` ∈ `_KERNEL_PATHS`
(`check_arbitration_kernel.py:95` — "hook library primitives"). O runbook da
S334 dizia que este pack não tocava kernel e estava ERRADO nesta metade. O
LAND arma `CEO_KERNEL_OVERRIDE` ele mesmo, no menor escopo, com o par
reason-SLUG + `I-ACCEPT` — o mecanismo idêntico ao do adrgate (land real
`cfab980`).

## Residuais declarados

- A perna state_file da spec §2 está APOSENTADA (r5 — falsificada duas
  vezes: mtime é o último tool-use e o rewrite atômico reseta o
  birthtime); `anchor_source="state_file"` permanece registrado no wire
  por compat, nunca produzido.
- `_session_start_ts` devolve `(ts, anchor_source)` — a spec §3 declara
  `-> Optional[float]`, mas o contrato de wire §4 exige `anchor_source` e
  nenhuma assinatura §3 o produz. Reconciliação MÍNIMA, documentada no
  docstring e no DESIGN; o teste §7.5 (kwargs exatos) passa.
- A entrada do noop-allowlist é INERTE para a heurística atual do detector
  (SessionEnd.py não é constant-emitter) — declarada porque a spec assinada
  a exige (§3, rota ADR-160 §7), não por disparo real hoje.
- `related_commits` do frontmatter não pode conter o sha do próprio land
  (não é conhecível antes de existir); o registro S335 no plano o declara.
- O rail de delta mede o próprio sujeito: `outcome=absent` dominante SEM
  mudança de comportamento na janela é o critério de MORTE pré-registrado
  (spec §8) — remover, não manter como dívida.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: APPROVED-BY-PLACEHOLDER
Plans: PLAN-179
Scope:
  - .claude/data/audit-registry.golden.txt
  - .claude/hooks/SessionEnd.py
  - .claude/hooks/_lib/audit_emit.py
  - .claude/hooks/check_postcompact_reinject.py
  - .claude/hooks/check_precompact_continuity.py
  - .claude/hooks/tests/test_audit_emit_api_contract.py
  - .claude/hooks/tests/test_audit_emit_plan163_lifecycle_actions.py
  - .claude/hooks/tests/test_check_compaction_continuity.py
  - .claude/hooks/tests/test_check_ledger_checkpoint.py
  - .claude/hooks/tests/test_codex_egress_proof_telemetry.py
  - .claude/hooks/tests/test_git_bypass_guard.py
  - .claude/hooks/tests/test_session_end_memory_delta.py
  - .claude/hooks/tests/test_w5_scrub_enforcement.py
  - .claude/plans/PLAN-179-context-continuity-durable-state.md
  - .claude/plans/PLAN-179/LEDGER.md
  - SPEC/v1/audit-log.schema.md
  - docs/CONTEXT-CONTINUITY-GUIDE.md
<!-- END SIGNED SCOPE -->
