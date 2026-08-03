---
id: PLAN-162
title: check_canonical_edit.py — S280 council 3-lane findings triage (12 advisory defects)
status: reviewed
created: 2026-07-27
reviewed_at: 2026-08-03
owner: CEO
depends_on: [PLAN-156-FOLLOWUP, PLAN-160]
budget_tokens: 120-180k
budget_sessions: 2
context_risk: medium
external_wait: none
tags: [canonical-edit, hooks, council, security, fail-open]
---

# PLAN-162 — check_canonical_edit.py council-S280 findings triage

## Context

S280 (2026-07-27) ran the first-ever **full 3-lane** `/council` over
`check_canonical_edit.py` (run `wf_ef98734e-7ec`, Owner-authorized egress;
closed PLAN-156-FOLLOWUP). Quorum FULL, `verify_failed=0`, and a strong
cross-vendor signal — 3/3 convergence on the top 3 defects, and each lane
independently caught 3 defects the other two missed (9/12 unique-catch).

The verdict was **FINDINGS**: 12 distinct ADVISORY defects against
`.claude/hooks/check_canonical_edit.py`. Per PROTOCOL V0–V3 the council
authorizes nothing — this plan is the intake that routes each finding to
FIX / ACCEPTED-BOUNDARY / DOCUMENTED-GAP, with real fixes going through
debate + (for kernel/canonical surfaces) the Owner GPG ceremony.

Full report: `.claude/plans/PLAN-156-FOLLOWUP/council-3lane-S280.md`.

**Dedup obligation (do FIRST):** several S280 findings may restate the
S276 W4 advisory set A/C/B/D on this same file (e.g. S280 #10 cache-key
staleness ≈ S276 B). Reconcile against
`PLAN-156-FOLLOWUP-council-livefire-findings.md` §W4 and against PLAN-160
(the prior canonical-edit hardening) BEFORE opening any fix — a finding
already fixed or already accepted is not re-litigated.

## The 12 findings (verbatim intake — classify, do not pre-judge)

| # | Raised by | Claim | First-read disposition (to VERIFY) |
|---|-----------|-------|-------------------------------------|
| 1 | claude+codex+grok | GPG `verify_detached(timeout=15.0)` L1011 > the hook's 5s registered timeout; block path verifies up to 12 sentinels/process → slow/deny-all GPG kills the hook → harness proceeds **fail-open** on canonical edits | LIKELY-FIX (fail-open on the block path is the worst class) |
| 2 | claude+codex+grok | `_find_sentinels` symlink-rejects only at depth ≤2 (L858-864) but discovery patterns are 4-5 deep → symlinked `PLAN-*`/audit-v2 dir routes an out-of-tree `approved.md` into discovery (F-01 bypass) | LIKELY-FIX (guard depth must cover the full pattern) |
| 3 | claude+codex+grok | ADR-121 signer registry `.claude/security/sentinel-signers-registry.yaml` is in neither `_CANONICAL_GUARDS` nor kernel deny; `.exists()`-gated (L1017) → an ordinary Edit/delete **silently disarms** the dual rail (asymmetric with the kernel-guarded legacy `.txt`) | LIKELY-FIX (trust-anchor; add guard + treat absence as fail-closed) |
| 4 | claude | Sentinel >64KiB falls Tier-1→Tier-2 (L1122/L1147); END marker is no scope terminator → Scope bullets OUTSIDE signed markers honored (containment loss, not fail-closed) | VERIFY (mitigant: .asc still signs whole file) |
| 5 | claude | `read_event`/`parse_error` both emit allow (L1450-1458) — INPUT-parse fail waved through, tension with PLAN-152 C4 fail-closed-on-input | CONTESTED (ADR-010 documents this as ENVELOPE/infra fail-open; the sibling kernel hook is fail-closed — reconcile the doctrine, may be ACCEPT) |
| 6 | claude | Layer-A MCP extraction reads only top-level str/list-of-str under 9 keys; nested `files:[{path,content}]` → 0 candidates → bypass | DOCUMENTED-GAP (v1 Layer-A; Layer B deferred — confirm still-intended) |
| 7 | codex | `uri` accepted (L355) but file URIs passed to `Path` with no scheme strip → `file://…/settings.json` classifies non-canonical even for a guarded file | VERIFY (oracle showed 0-vs-1 split) |
| 8 | codex | Policy hash-pin registry `.claude/policies/.drift-manifest.json` matches no guard pattern + not kernel → rewritable without the sentinel it pins | LIKELY-FIX (parallels #3 — pin the pinner) |
| 9 | codex | Veto audits hard-code `blocked_tool="Edit|Write|MultiEdit"` (L1186/L1308) vs `event.tool_name`; hook is registered for `mcp__.*` too → MCP/apply-patch blocks forensically misattributed | LIKELY-FIX (forensic fidelity, low blast) |
| 10 | grok | `_compute_sentinel_cache_key` hashes only sentinel bytes+stat+target (L903-916); .asc/allowlist/registry mutations don't bust the key (comment claims otherwise) | VERIFY vs S276 B — likely SAME defect, re-confirmed (mitigant: per-process cache) |
| 11 | grok | Invisible-unicode SKILL.md guard keys only on single `file_path` (L1556/L1649-1651); other GRANTED SKILL.md paths in a multi-candidate event unscanned under `CEO_UNICODE_HARDBLOCK=1` | VERIFY |
| 12 | grok | Dispatcher YAML guarded as `*.{yaml,yml}` while `**` applies only to `*.py` (L164-167) → nested `dispatcher/**/*.yaml` ungated | LOW (no nested YAML on disk; mitigant: kernel hard-deny covers `dispatcher/**/*`) |

## Waves

- **W0 — debate + dedup. ✅ DONE 2026-08-03.** Três lanes (Security /
  Code Reviewer / QA), **3× ADJUST, zero VETO**, veredito
  `PROCEED` / `design-coherent`. Consenso completo, com as 14 revisões de
  disposição, em `.claude/plans/PLAN-162/debate/round-1/consensus.md`.
  Resumo do que MUDOU (a triagem sobreviveu; a especificação dos fixes
  não):
  - **12/12 findings reproduzem no HEAD** — nenhuma STALE em substância;
    três com line numbers deslocados (#5 real `:1902-1909`, #11 real
    `:2133-2145`, #9 sub-escopado).
  - **#1 re-diagnosticado**: não é latência (1 GPG ≈ 17 ms), é
    amplificação O(candidatos × sentinels) — a chave de cache inclui
    `target_rel` enquanto a verificação de assinatura é independente do
    alvo. Medido: **4.16 s de um budget de 5 s** num evento de 20
    caminhos, 0 hits / 320 misses. Fix = partição de cache; **fold #1+#10**.
  - **Cap de sentinels REMOVIDO** (era regressão: o sentinel que pararia
    de conceder é o da cerimônia recém-assinada). Deadline global
    fail-closed no lugar, constante de módulo + teste de drift (ler o
    budget de `settings.json` em runtime é circular).
  - **A citação de ADR-010 para o #5 é FALSA** (zero ocorrências de
    postura de falha no ADR). #5 racha: 5a `read_event` → ACCEPT;
    5b `parse_error` → **FIX fail-closed**.
  - **#4 estreitado** ("parse só dentro dos markers" brickaria 5 dos 16
    sentinels vivos); **#9 ampliado** para 4 sítios + validação de
    `tool_name`; **#11 → DOC-GAP** (inexequível sob Layer-A v1);
    **#2 → fix independente de profundidade**.
  - **Rider R1 (check_budget) REJEITADO como proposto** — 3/3: o
    breadcrumb já existe, o hook não tem caminho de bloqueio nenhum
    (advisory por ADR-033), e a heurística CWD/branch contradiz T-001.
    Re-desenhado: comparar cada plano ativo contra o PRÓPRIO cap.
  - **P0 NOVO, fora das 12 (S1)**: `fnmatch.fnmatchcase` nos dois rails +
    filesystem case-insensitive (APFS) ⇒ `.claude/settings.JSON` e
    `.claude/hooks/_lib/audit_emit.PY` furam **canonical E kernel**, e a
    escrita sobrescreve o arquivo real. Verificado em primeira mão pelo
    CEO. Entra como FIX P0.
  - **S3**: #1 já é residual ACEITO em `ADR-164:119-127` ⟹ o entregável
    inclui **`ADR-164-AMEND-1`** (a medição refuta a premissa "512 paths,
    operationally absurd": 47 bastam).
  - **S8** (adendo pós-consenso): o deadline do #1 exige **clock
    injetável no FIX** — sem seam, o teste red-first vira `sleep` real e
    flaky sob carga (classe já documentada neste repo).

- **W0-B — pair-rail cross-model sobre o diff (3 rodadas, S291).** O
  Stop-hook exigiu review antes do commit; rodei até parar de achar.
  Duas correções que nenhum dos 3 lanes do debate pegou:
  - **R1/P1 — a classe vacuous-gate tem CAMADAS.** Eu consertei a regra
    morta (`registered` casava 0 docs) e a corrigida passou a casar 5,
    o que a fez PARECER viva — enquanto `docs/GUIA-COMPLETO.md:86`, com a
    preposição diferente ("hooks wired **in**"), seguia stale em 44 com 46
    vivos. Meu próprio teste de liveness não pegou (a métrica tinha
    matches > 0). **Uma regra que casa ALGUNS documentos é
    indistinguível de uma que casa todos**: a prova é controle positivo
    por SITE, não contagem por métrica.
  - **R2/P1 — a mitigação do S2 que eu escrevi era defeituosa.** "Aceitar
    sentinels rastreados no git **ou** pré-existentes à sessão" é
    derrotável em um comando: o agente escreve o `approved.md` e roda
    `git add`; `ls-files --error-unmatch` passa a chamá-lo tracked. Pior,
    o teste de controle comitava um sentinel criado pelo próprio teste e
    afirmava que ele CONCEDE — codificando o bypass como comportamento
    desejado. Corrigido: anchor = **início da sessão**, três negativos
    (untracked / staged / committed).
  - **R2/P2 — dois sites de versão mortos de nascença.** `CLAUDE.md` e
    `README.md` nunca tiveram `VERSION=` (`git log -S` não acha commit
    que o adicionasse), e o checklist de release que escrevi nesta mesma
    sessão os anunciava como checados. Removidos + liveness estendida à
    família inteira de versão (incl. `npm/package.json`,
    `pyproject.toml`): site declarado com zero matches agora FALHA como
    "dead release gate".
- **W1 — red-first tests** para cada FIX, na convenção `PLAN162_FIX_<N>` +
  `xfail(strict=True)` herdada de `test_canonical_edit_council_findings.py`
  (o precedente do PLAN-160 para provar fix em hook canonical-guarded).
  #10 exige teste IN-PROCESS (subprocess mata o cache e dá XPASS por
  acidente). Inclui ≥1 passada de INTERAÇÃO entre findings.
- **W2 — fixes** em staged pack + pair-rail APPROVE + cerimônia GPG do
  Owner. O Scope do sentinel deve deixar os fixes fail-closed
  SEPARÁVEIS dos riders (um REJECT do rail num rider não pode travar
  todos).
- **W3 — council re-run: PULADO.** Ratificado pelo Owner 2026-08-03
  (AskUserQuestion, opção "Pular W3"): *"Cada FIX exige teste red-first
  (falha antes, passa depois) + o diff inteiro passa pelo pair-rail codex
  na cerimônia."* 3/3 lanes concordaram.

## Open questions — RESOLVIDAS no W0

- **OQ1 → 5a ACCEPT / 5b FIX.** A assimetria alegada é metade falsa: o
  kernel irmão é fail-open IDÊNTICO em `read_event`
  (`check_arbitration_kernel.py:541-543`); os hooks divergem só em
  `parse_error`, e ali o sentinel é o DRIFT (CLAUDE.md §4 é literal:
  fail-closed on INPUT). Não há emenda a fazer em ADR-010 — não há texto
  para emendar; falta DOCUMENTAR a postura. **Teste-alfinete obrigatório
  de qualquer jeito**: `grep parse_error` nos 8 arquivos de teste = ZERO.
- **OQ2 → FOLD mantido** (3/3), sem herdar o enquadramento "low" do #12:
  #3 e #8 estão DUPLAMENTE desguardados (nem canonical nem kernel),
  enquanto #12 tem kernel hard-deny.
- **OQ3 → DEFER** para plano próprio (3/3). Não é `check_canonical_edit`.

## Success criteria

- [ ] Every one of the 12 findings has a recorded disposition (FIX / ACCEPT /
  DOC-GAP) with evidence, deduped against S276 + PLAN-160.
- [ ] Every FIX has a red-first test that fails before and passes after.
- [ ] Canonical/kernel fixes land via pair-rail-APPROVE + Owner GPG ceremony.
- [ ] Validate green on the closeout commit.
