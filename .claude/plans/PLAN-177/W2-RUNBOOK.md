# W2 — Runbook do corte rc.4 (ordem CF-7, imutável)

> Cada passo numerado. NÃO reordenar — a ordem foi o MF-5 do debate:
> na ordem antiga o próprio guard mataria a tag (E_DELTA/E_VACUOUS).

## Pré-condições (antes de QUALQUER passo)
- [ ] Pack W1 landado (cerimônia GPG do Owner concluída)
- [ ] `gh variable list` — `CEO_PAIR_RAIL_VERDICT_OPTIONAL` e
      `CEO_SOTA_DISABLE` ausentes ou `0` (CF-3)
- [ ] Margem do smoke-install: duração do último run vs
      `timeout-minutes: 25` — margem <20% ⇒ bump ANTES da tag
- [ ] Árvore limpa; `origin/main == HEAD`

## Sequência
1. `bump --rc 4` (via release.sh; `--today` explícito) → commit+push.
   Estado alvo: "curas + bump" TODOS em main. CI verde POR-JOB
   (success, nunca cancelled/skipped — smoke-install tem
   cancel-in-progress), pinado a `SHA=$(git rev-parse HEAD)`.
2. Re-pass Codex revisa ESSE SHA (worktree DETACHED limpo no SHA;
   payload redigido; até APPROVE). Evidência →
   `.claude/plans/PLAN-177/repass-rc4/` (manifesto sha256 rastreado).
3. Autorar envelope `pair-rail-verdict-v1.3.0-rc.4.md`:
   - `verdict:` do conjunto {GO, GO-WITH-CONDITIONS} — o gate novo
     REJEITA ausente/duplicado/malformado (nossa própria cura)
   - `parent_sha` = parent revisado; `inputs_hash` RECOMPUTADO
     (R-1: a cura mudou o hash — o valor da rc.3 NÃO serve)
   - delta_allowlist = SÓ envelope + verdict-fields + evidência
     `PLAN-177/repass-rc4/**`
   - **ÚLTIMA escrita antes da tag** — nenhum path do
     `pair-rail-inputs-hash-manifest.txt` tocado depois (B-U3)
4. Commit do envelope → push → CI verde por-job no SHA do envelope.
5. `preflight --rc 4` (sobre EXATAMENTE o commit que será taggeado;
   assert `git rev-parse HEAD == SHA`).
6. **[OWNER]** tag `v1.3.0-rc.4` (assinada) → push da tag → CI da tag
   verde → GitHub pre-release. `npm-publish.yml:443` é a última
   barreira (remote tag ainda aponta o SHA do run).
7. Hold ADR-103 **24h** a partir da tag.

## D+1 — GA (runbook separado, gerar HOJE à noite ou amanhã)
- OWNER-GA-CUT **RETARGETADO** (codex v4 P1-2): RC_TAG=v1.3.0-rc.4,
  freeze-SHA da rc.4, evidência `repass-ga-rc4/` fresca. O script da
  rc.3 NÃO serve (pinado em rc.3 nas 3 dimensões).
- Header do GA-CUT corrigido (aceita SÓ `VERDICT: GO` exato do rail
  bruto, by design; rail final `GO-WITH-CONDITIONS` = triagem com o
  Owner, não bug).
- `origin/main == SHA(rc.4)` no momento do verdito GA; avançou ⇒ rc.5.
- Pós-GA: remover a limitação "OPEN P1" do CLAUDE.md §5 + W3/169 SÓ
  com re-staging dos 3 scripts + re-pin do gate-scripts-manifest
  (R-2 ampliado — cp cego reverteria a cura P1-1).
