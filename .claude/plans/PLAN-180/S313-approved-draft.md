# S313-approved — sentinel do trem S313 (DRAFT — assinar como S313-approved.md)

> Assinatura em um passo: `! bash ~/canhada-labs/OWNER-S313-SIGN.sh`
> (gera este arquivo com Anchor-SHA real, assina, dry-run, land).

Plan: PLAN-180
Wave: follow-up do land W0-W2 (`996d72b`) + W3 (carona)
Anchor-SHA: <HEAD-NO-MOMENTO-DA-ASSINATURA>
Data: <AAAA-MM-DD>

## Scope

```
scripts/upgrade.sh
scripts/tests/test-schema-generation-pins-unit.sh
.github/workflows/smoke-install.yml
.claude/adr/ADR-081-token-as-time-unit.md
.claude/workflows/council-audit.js
```

## O que este trem muda

1. **Cura do Smoke Install vermelho (`e5ce982`+).** `scripts/upgrade.sh`
   refresca `PLAN-SCHEMA.md`/`DEBATE-SCHEMA.md` HASH-GATED contra uma
   lista escrita à mão de gerações prévias. O land `996d72b` (PLAN-180
   W0-W2, `eta_calendar` no schema) mudou o `PLAN-SCHEMA.md` sem apendar
   o hash da geração que substituiu (`8ca4f866…`, a shipada em
   v1.2.0/v1.3.0) — todo adopter nessa geração fica PRESERVED = STALE
   fatal no parity e2e (modos maintainer e user). Cura de instância: +1
   hash na lista. Contrato explicitado no comentário do código.
2. **Guard de classe** `scripts/tests/test-schema-generation-pins-unit.sh`:
   deriva o conjunto de gerações de **git** (bytes de cada doc em toda
   release tag `v*` + histórico completo quando o clone não é shallow) e
   exige que toda geração ≠ HEAD esteja na lista do upgrade.sh. Zero
   gerações enumeráveis = falha de SCAFFOLD (exit 2), nunca skip verde;
   cobertura impressa. Root resolvido por `git rev-parse --show-toplevel`
   (a 1ª versão resolvia por path e gradeou o STAGED achando que era o
   vivo — controle negativo morto, pego antes de entrar no pack).
3. **`smoke-install.yml`**: busca TODAS as tags `v*` (depth 1), roda o guard
   por-PR, e o `paths:` filter passa a incluir o guard + os dois schema
   docs (um commit que só mexe no schema tem de acender este gate).
4. **Carona PLAN-180 W3, Edit 1**: `ADR-081` `enforcement_commit: pending`
   → `996d72b811c04fed73be6f3ddbf820834d96d87d`.
5. **Carona PLAN-180 W3, Edit 2**: bullet ADR-081 (tokens+sessões; prazo
   humano SÓ para `external_wait`) no `laneBrief` das lanes externas do
   `council-audit.js` — a NOTA W3 apontava `council.md`, mas o template do
   prompt externo vive no workflow; superfície corrigida. 6 testes que
   tocam o arquivo verdes na simulação.

## Prova pré-assinatura (S313, clone local com o pack aplicado)

`bash -n`, guard (verde no staged / vermelho no HEAD = controle negativo
vivo), actionlint, yaml, gate-scripts manifest, verify-counts, claims,
pytest (4 arquivos council/redactor/class-guard), grok-artifact,
council-fixture — 9/9 verde, rc agregado 0. **Parity e2e REAL** (o
instrumento que estava vermelho no CI) rodado no mesmo clone com o pack:
`verdict(mode=maintainer): PARITY`, `verdict(mode=user): PARITY`,
STALE=0, `RESULT: PASS`, rc=0.

## Depois do land

Flip do PLAN-180 `executing→done` com `related_commits` (W0-W2 + W3) e
`completed_at` — regra `check_plan_edit`, decisão do Owner.
