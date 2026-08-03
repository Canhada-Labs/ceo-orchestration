---
plan: PLAN-162
round: 1
created_at: 2026-08-03
proposer: CEO
---

# PLAN-162 round-1 proposal — triage das 12 findings do council S280

> Plano completo: `.claude/plans/PLAN-162-canonical-edit-council-s280-triage.md`
> Report do council: `.claude/plans/PLAN-156-FOLLOWUP/council-3lane-S280.md`
> Alvo: `.claude/hooks/check_canonical_edit.py` (canonical-guarded; fixes
> landam via staged pack + pair-rail + cerimônia GPG do Owner)

## Tese

O council 3-lane S280 (quorum FULL, verify_failed=0) produziu 12 defeitos
ADVISORY contra o hook canonical-edit. Este debate fecha a disposição
por-finding (FIX / ACCEPT / DOC-GAP), com verificação obrigatória contra o
HEAD ATUAL (os line numbers citados são de 2026-07-27; PLAN-160 e a
cerimônia PLAN-164 mexeram no arquivo depois de alguns dos achados
originais S276).

## Dedup executado (obrigação do plano — feita antes deste debate)

Contra o advisory set S276 W4 (run `wf_cd40731f-205`) e PLAN-160:

| S280 | ≈ S276 | Estado |
|------|--------|--------|
| #10 cache-key staleness | **B** (revocation staleness) | S276 B NÃO entrou no fix do PLAN-160 (W2 fixou só os confirmados A/C/D); S280 re-confirmou pós-160 com o comentário falso ainda no lugar. É o MESMO defeito, agora 2× confirmado cross-vendor. |
| #5 parse-error → allow | **E** (envelope parse) | S276 E foi CONTESTED→ACCEPT: ADR-010 define envelope/infra fail-open como contrato. O sibling kernel hook é fail-closed — assimetria a reconciliar (OQ1). |
| #6 Layer-A nested MCP | **F** (documented boundary) | S276 F = boundary documentada, Layer B cobre por design. |
| #1-#4, #7-#9, #11-#12 | — | Novos no S280 (sem par no S276/PLAN-160). |

PLAN-160 já FIXOU (cerimônia S277, não re-litigar): A (multi-candidate
first-break bypass), C (fail-open dead-except em decide()), D (CWD-anchored
relative resolve).

## Disposições propostas (a verificar por vocês contra o HEAD)

| # | Claim (resumo) | Proposta CEO | Racional |
|---|----------------|--------------|----------|
| 1 | GPG verify timeout 15s × budget do hook; até 12 sentinels/processo → hook morto pelo harness = fail-open no BLOCK path | **FIX (prioridade 1)** | Pior classe possível: o guard morre e o harness prossegue. Fix = orçamento de verificação derivado do budget registrado (o hook sempre RESPONDE — block ou allow — antes de ser morto), cap de sentinels verificados, GPG lento ⇒ sentinel tratado como não-verificado (sem grant) e não como allow. |
| 2 | symlink-reject só em depth ≤2, discovery patterns 4-5 deep → approved.md fora da árvore via symlink | **FIX** | Guard depth tem de cobrir a profundidade real dos patterns (re-abre a família F-01 do PLAN-152). |
| 3 | signer registry ADR-121 fora de _CANONICAL_GUARDS + `.exists()`-gated → Edit comum desarma o dual-rail em silêncio | **FIX** | Trust-anchor desguardado. Guard no registry + ausência = fail-closed quando o dual-rail é esperado (assimetria com o .txt legacy kernel-guarded). |
| 4 | Sentinel >64KiB cai Tier-1→Tier-2; END marker não termina Scope → bullets FORA dos markers assinados honrados | **FIX (se confirmado)** | Perda de contenção de escopo. Fix = Scope parse APENAS dentro dos markers assinados; oversize ⇒ reject fail-closed, não downgrade. Mitigante (.asc assina o arquivo todo) reduz severidade, não elimina a classe. |
| 5 | read_event/parse_error → allow | **ACCEPT + DOC** | ADR-010: envelope/infra é fail-open; matchers de segurança são fail-closed em INPUT (PLAN-152 C4). read_event é envelope. Documentar in-code citando ADR-010 e a assimetria deliberada com o kernel hook (tier mais alto = postura mais dura). OQ1 abaixo. |
| 6 | Layer-A não vê nested `files:[{path,content}]` | **DOC-GAP (confirmar intenção)** | = S276 F. Layer B (server-side canonical_guard, PLAN-070) cobre MCP writes por design. Documentar a dependência in-code. |
| 7 | `file://` URI → Path sem scheme-strip → classifica não-canonical | **FIX (se confirmado)** | Normalização barata; oracle S280 mostrou split 0-vs-1. |
| 8 | `.drift-manifest.json` (hash-pin registry) reescrevível sem sentinel | **FIX — FOLD com #3** | Mesma classe "guard-the-guardfiles". Um patch, uma seção, dois alvos. |
| 9 | audits hard-codam blocked_tool="Edit\|Write\|MultiEdit" vs event.tool_name (hook registrado p/ mcp__.* também) | **FIX** | Fidelidade forense, blast baixo. |
| 10 | cache key não inclui .asc/allowlist/registry (comentário afirma o contrário) | **FIX** | = S276 B, 2× confirmado. Key passa a incluir digest/mtime de .asc + allowlist + registry; comentário corrigido. Mitigante per-process não segura sessão longa. |
| 11 | unicode guard só no file_path único; multi-candidate SKILL.md sem scan sob CEO_UNICODE_HARDBLOCK=1 | **FIX (se confirmado)** | Cobertura do guard deve seguir o conjunto GRANTED, não o primeiro path. |
| 12 | dispatcher `**/*.yaml` nested ungated | **ACCEPT + DOC** | Sem YAML nested em disco + kernel hard-deny cobre `dispatcher/**/*`. Registrar como residual nomeado; re-visitar se nested YAML nascer. |

## Riders (mesma cerimônia, arquivos distintos)

- **R1 — check_budget skip-silencioso** (`.claude/hooks/check_budget.py`):
  com 3 planos ativos o check degrada para no-op silencioso ("indeterminate
  plan_id — skipping"; 20 ocorrências no audit-log durante o arco mais caro
  da história, ~17,5M tokens, S284 — zero enforcement). Proposta: **FIX** —
  em ambiguidade, escolher determinístico (plano do CWD/branch se derivável;
  senão o de budget mais restritivo) E avisar alto (stderr + audit event),
  nunca skip mudo. Desenho exato a debater.
- **R2 — instrumento do council (OQ3 do plano)**: recalibrar C3 wall-clock +
  transport-decode do args. Proposta: **DEFER** para plano próprio de
  manutenção (não é check_canonical_edit; não atrasar esta cerimônia).

## Open questions para o debate

- **OQ1**: #5 — a assimetria sentinel-hook (fail-open) vs kernel-hook
  (fail-closed) em parse_error é deliberada ou drift? Proposta: deliberada
  (tier), documentar. Se o debate decidir fail-closed, é mudança de
  contrato ADR-010 → precisa emenda de ADR, não só código.
- **OQ2**: #3+#8 fold — alguma razão para MANTER separados?
- **OQ3**: #1 — fail-closed no GPG lento pode negar cerimônia legítima sob
  carga (DoS-por-lentidão do próprio gate). Qual o balanço certo entre
  "hook sempre responde" e "cerimônia sob carga ainda funciona"?

## Contexto de execução (W1/W2 pós-debate)

- Cada FIX exige teste red-first em `hooks/tests/` (não-guarded) que falha
  ANTES e passa DEPOIS; TestEnvContext + mock.patch.dict obrigatórios.
- Fixes em staged pack (`PLAN-162/ceremony-staged/`) + MANIFEST.sha256
  rastreado; pair-rail codex sobre o diff; cerimônia GPG única consolidada
  (junto com P1/P2 do PLAN-165, RC3-F7, ADR-110-AMEND-2).
- W3 (council re-run de confirmação): **PULADO** — ratificado pelo Owner
  2026-08-03 via AskUserQuestion ("Pular W3"): verificação = red-first
  tests + pair-rail codex da cerimônia.

## O que eu NÃO proponho mudar

- Contrato ADR-010 (envelope fail-open) — salvo consenso em contrário.
- Layer-A v1 (nested MCP fica com Layer B) — custo/benefício de parse
  profundo no hot path não fecha.
- Qualquer literal de timeout do pair-rail (isso é ADR-110-AMEND-2, outro
  debate).
