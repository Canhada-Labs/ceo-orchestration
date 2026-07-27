# HANDOFF S279 — PLAN-161 maintenance sweep: cerimônia W2 + L3 egress (Owner)

> **Estado ao entregar:** W1 LANDADO em main (testes red-first + V1 docs/verify-counts
> + H1). Pack W2 (**38 arquivos**, 6 concerns, 3 segmentos KERNEL) construído, verificado
> em clone limpo por concern, verificado COMBINADO pelo `land-plan161.sh --preflight-only`
> (**15/15 oracles GREEN, 6/6 concerns APPLY**), e revisado pelo pair-rail codex por
> **8 rodadas até APPROVE explícito** (findings 10→5→4→4→3→2→1→APPROVE; cada finding
> corrigido ou rebatido-com-evidência, cada fix provado red-first; transcripts em
> `.claude/plans/PLAN-161/pair-rail/w2-round-{1..8}*.md`). Manifesto sha256 RASTREADO
> (`inputs.sha256`, **38 entradas**) + 3 basepins de kernel. O staged/ é gitignored e
> MACHINE-LOCAL — rode tudo a partir DESTE checkout.
>
> **AINDA NÃO PUSHADO.** Os commits de materiais (W1 + plano + pair-rail) estão em
> main local; `git push origin main` antes da cerimônia (o preflight exige
> HEAD==origin/main no run real). A cerimônia em si adiciona ATÉ 6 commits novos.

## Passo 1 — Cerimônia W2 (GPG)

```bash
# ensaio completo (aplica + verifica + RESTAURA a árvore; sem GPG, sem commit):
!bash .claude/plans/PLAN-161/land-plan161.sh --dry-run

# cerimônia real (assina o sentinel inline + até 6 commits segmentados -S):
!export GPG_TTY=$(tty); gpgconf --kill gpg-agent
!bash .claude/plans/PLAN-161/land-plan161.sh
!git push origin main
```

- Preflight fail-closed: branch, tree pristine, `shasum -c inputs.sha256`,
  origin-sync, Validate verde no HEAD, chave GPG, 3 basepins, batalha de oracles
  num overlay (os oracles W1 red-first PRECISAM flipar verde lá).
- Drop-out CF-8: concern com oracle vermelho é DROPADO e deferido — não trava o lote.
- O sentinel nomeia a concentração de 5 guard-classes (CF-5/R-9) — assine ciente.
- SPEC (install-cli.md + audit-log.schema.md) é aplicado via cp sob sentinel
  (deny-Edit cobre só a tool). ADR count fica em 180 (4 amendments in-place).

## Passo 2 — L1: prova do lint (após o push)

Abra uma sessão `claude` fresca neste repo: ZERO warnings `Permission deny rule`
(eram 3). Depois: probe positivo de Write-denial — com só `Edit(PROTOCOL.md)` no
deny, um Write no PROTOCOL.md deve ser recusado PELA CAMADA DE PERMISSÃO
(mensagem distinta do `CANONICAL-EDIT-BLOCKED` do hook).

## Passo 3 — L3: council 3-lane [AUTORIZAÇÃO DE EGRESS SUA]

O fix do grok arg-contract (C2) + budget do codex (C3) destravam a 3ª lane.
Escopo estreito (cabe no budget): `check_canonical_edit.py`.

```bash
# na sessão Claude: /council check_canonical_edit.py
```

Resultados (r5 F1 do plano):
- (a) CLEAN 3-lane + verify_failed=0 → PLAN-156-FOLLOWUP flipa
  reviewed → executing → done (o único critério aberto dele é essa rodada).
- (b) DEGRADADO por causa NOVA → registrar + decidir (OQ3): se você ACEITAR o
  2-lane documentado, o FOLLOWUP fecha do mesmo jeito com a aceitação registrada.
- (c) HOLD → FOLLOWUP fica reviewed e o L3 fica aberto.

## Passo 4 — L4: prova de liveness (1 review pós-land)

O modo default do Stop-hook é detect-only (`detected_only` = neutro, nunca
esverdeia). A prova exige UM review real pós-land:

```bash
# num diff arriscado qualquer (ou um throwaway):
!export CEO_CODEX_USER_REVIEW_AUTO=1
# ... sessão com diff risky → Stop hook roda codex → verdict parseado emite
#     codex_review_verdict {clean|findings} ...
# depois: /ceo-boot → failopen_rail_liveness_7d deve ficar VERDE
# (stop_review: healthy>=1 ∧ failopen==0; pair_rail: activity-conditioned)
```

## Fechamento (quando 1-4 concluídos)

- PLAN-161 → done (executing → done + completed_at + related_commits).
- PLAN-156-FOLLOWUP → done via executing (se L3 (a) ou (b)).
- Sidecar audit-log.errors (19 linhas, tudo 07-14/15, classes benignas):
  zerar é opcional e seu (`!: > ~/.claude/projects/ceo-orchestration/audit-log.errors`).

## Rollback

- Antes do push: `git reset --hard <sha pré-cerimônia>` (o script imprime).
- Depois do push: `git revert <shas dos segmentos>`.
- Perf-gate: killswitch amplo `CEO_SOTA_DISABLE=1` (repo var) segue disponível.
