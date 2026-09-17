---
id: PLAN-190-FOLLOWUP-audit-actions
title: Eventos de auditoria para o ledger de lançamento de Workflow (bloqueio, override, orphan)
status: draft
created: 2026-09-17
owner: CEO
depends_on: [PLAN-190]
level: L3
tags: [audit, workflow, followup]
---

## Context

A W1 do PLAN-190 grava o ledger de lançamento em JSON (mode 0600) e o índice `launches.jsonl` sob o
diretório de estado do projeto, e NÃO emite evento de auditoria: registrar uma ação nova em
`_lib/audit_emit._KNOWN_ACTIONS` (+ ramo de scrub + linha no `SPEC/v1`) é cerimônia do dono do audit,
e emitir uma ação não registrada é descartado em silêncio (falsa telemetria). Os três críticos do
debate r1 e o rail pediram que o follow-up fosse NOMEADO antes da assinatura: uma decisão de BLOQUEIO
e, sobretudo, um OVERRIDE (`mismatch_forced`, token de `force` com motivo) ficam hoje fora da cadeia
HMAC — um arquivo 0600 editável, sem tamper-evidence (R-SEC6 da crítica de segurança).

## Goal

Toda decisão do guard que muda o curso de um run (`mismatch_blocked`, `mismatch_forced`,
`mismatch_script_advisory`, `orphan`) entra na cadeia HMAC como evento com ação registrada, campos
fechados e sem conteúdo do operador (contagens e hashes; nunca chaves nem valores de `args`).

## Items

### W1 — Registro das ações  [P0]  (canônico: `_lib/audit_emit.py`, `SPEC/v1/audit-log.schema.md`)
- `workflow_launch_recorded` {launch_id, script_sha256, args_sha256, resume_from_run_id|null}
- `workflow_resume_guard` {launch_id, run_id, result ∈ {match, mismatch_blocked, mismatch_forced,
  mismatch_advisory, mismatch_advisory_weak_bind, mismatch_script_advisory, mismatch_script_blocked,
  inconclusive, no_manifest, resume_id_unrecognised}, counts {changed, only_recorded, only_now},
  force_reason_sha256|null}
- `workflow_run_bound` {launch_id, run_id, bind_method} · `workflow_run_orphan` {run_id, reason}
- Ramo de scrub: nenhum campo livre além de `result`/`bind_method`/`reason` (enums fechados).

### W2 — Emissão no hook  [P0]  (canônico: `check_workflow_launch.py`)
- `from _lib import audit_emit` NA CHAMADA (classe audit_emit-stale); fail-open; nunca bloqueia por
  falha de emissão.

### W3 — Gate de coerência  [P1]
- Teste que TODA linha do índice `launches.jsonl` com `kind ∈ {launch, bind, orphan, force_token}`
  tem um evento correspondente na cadeia (amostra por sessão); `ceo-launches.py report` cruza os dois.

## Regra de parada
- Se o registro das ações exigir mudar o esquema além de acrescentar linhas (nova versão do SPEC),
  parar e abrir ADR — não emendar por conveniência.
