# wave-cli — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`, lição do `wave-w1-followup-approved.md`).
> O binding é o `Patch-sha256` (land por PATCH, sem `MANIFEST-*`). O
> `Anchor-SHA` é preenchido pelo `OWNER-S326-SIGN.sh` com `git rev-parse HEAD`
> no momento da assinatura; o `OWNER-S326-LAND.sh` aborta no G3 se não casar.
> Reescrever um byte deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-182
Wave: wave-cli (OQ-6 — CLI do resolvedor único; Axis 3 do isolamento de testes; manifesto ADR-192)
Patch: .claude/plans/PLAN-182/cli-ceremony/S326-CLI-CEREMONY.patch
Patch-sha256: fa78673e5f394ef62ad1a6b6b87dd2b3d9b7d3fe89515aa96aa2edb4942da38b
Anchor-SHA: 318d0bcc0fbfb4f1a5dc126aa066c06d148fd2cd
Data: 2026-08-24

## Autorização de governança

- **OQ-6 decidida pelo Owner em 2026-08-22 (S322), texto verbatim no plano** (§766 e §OQ-6):
  *"Expor CLI no runtime_paths.py (Recomendado) — Adiciono `__main__` ao módulo, os templates
  passam a chamar o resolvedor único em vez de reconstruir o literal. Fecha o item e mata a classe
  na raiz — o adopter deixa de receber o defeito. É a cura, não o contorno."*
- **Foco ratificado em 2026-08-24** (bloco no topo do PLAN-182) e **ordem do dia ratificada em chat
  na S326** (cerimônia #1 = CLI; cura estrutural do achado S326 embarcada no mesmo pacote).
- **Debate L3 do PLAN-182:** round 1 fechado com PROCEED (S315); a W1 landou sob `S319-approved.md`
  e o follow-up sob `wave-w1-followup-approved.md` (S321). Esta wave executa uma decisão já
  tomada (OQ-6), não abre desenho novo.
- **Pair-rail (V2 do PROTOCOL):** rodadas registradas em `cli-ceremony/rail-round-*.md`; a
  última rodada sem achado P0/P1 é a condição de assinatura.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Plans: PLAN-182
Scope:
  - .claude/governance/gate-scripts-manifest.txt
  - .claude/hooks/_lib/runtime_paths.py
  - .claude/hooks/_lib/test_isolation.py
  - .claude/hooks/tests/test_collect_only_audit_isolation.py
  - .claude/hooks/tests/test_runtime_paths.py
  - .claude/plans/PLAN-182-audit-path-isolation.md
  - .claude/scripts/ceo-backup.sh
  - .claude/scripts/ceo-restore.sh
  - .claude/scripts/local/verify-counts.sh
  - .claude/scripts/tests/test_templates_use_single_resolver.py
  - templates/codex/pre-push-review-gate.sh
  - templates/grok/pre-push-review-gate.sh
<!-- END SIGNED SCOPE -->

## Residual declarado

- `--project` no CLI muda só o INPUT do slug; `CLAUDE_PROJECT_DIR_NATIVE` continua vencendo para
  `--state-dir` — é o override documentado do operador (ADR-001), não um default.
- Nos templates, resolvedor ausente (upgrade parcial) degrada o path (b) do gate para
  INDISPONÍVEL com nota no stderr; os trailers `Pair-Rail-Reviewed: APPROVE` seguem liberando o
  push — a mesma degradação que a falha do oráculo já toma. Nunca fallback para literal.
